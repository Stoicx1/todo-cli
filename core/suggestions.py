"""
Local AI Suggestions - No OpenAI API required
Provides intelligent task insights and suggestions using local analysis
"""

from typing import List, Dict, Tuple
from collections import Counter
from datetime import datetime
from models.task import Task
from core.state import AppState


class LocalSuggestions:
    """
    Provides intelligent suggestions without external API calls
    """

    @staticmethod
    def analyze_tasks(state: AppState) -> Dict[str, any]:
        """
        Analyze task list and provide statistics
        Returns comprehensive task analysis
        """
        if not state.tasks:
            return {
                'total': 0,
                'completed': 0,
                'incomplete': 0,
                'completion_rate': 0.0,
                'by_priority': {},
                'by_tag': {},
                'suggestions': []
            }

        total = len(state.tasks)
        completed = sum(1 for t in state.tasks if t.done)
        incomplete = total - completed

        # Group by priority
        by_priority = Counter(t.priority for t in state.tasks if not t.done)

        # Group by tag
        by_tag = Counter(t.tag for t in state.tasks if t.tag and not t.done)

        completion_rate = (completed / total * 100) if total > 0 else 0

        return {
            'total': total,
            'completed': completed,
            'incomplete': incomplete,
            'completion_rate': completion_rate,
            'by_priority': dict(by_priority),
            'by_tag': dict(by_tag),
            'high_priority_count': by_priority.get(1, 0),
            'medium_priority_count': by_priority.get(2, 0),
            'low_priority_count': by_priority.get(3, 0)
        }

    @staticmethod
    def get_smart_suggestions(state: AppState) -> List[str]:
        """
        Generate smart suggestions based on task analysis
        Returns list of actionable suggestions
        """
        if not state.tasks:
            return ["💡 Start by adding your first task with '/add' or 'add'"]

        suggestions = []
        analysis = LocalSuggestions.analyze_tasks(state)

        # Completion rate suggestions
        if analysis['completion_rate'] < 20:
            suggestions.append("🎯 Low completion rate detected. Focus on completing a few high-priority tasks.")
        elif analysis['completion_rate'] > 80:
            suggestions.append("🎉 Great progress! You've completed most of your tasks.")

        # Priority-based suggestions
        if analysis['high_priority_count'] > 5:
            suggestions.append(f"⚠️ You have {analysis['high_priority_count']} high-priority tasks. Consider focusing on these first.")

        if analysis['high_priority_count'] == 0 and analysis['incomplete'] > 0:
            suggestions.append("✨ No high-priority tasks! Start with medium priority items.")

        # Tag-based suggestions
        if analysis['by_tag']:
            most_common_tag = max(analysis['by_tag'].items(), key=lambda x: x[1])
            suggestions.append(f"📊 Most active tag: '{most_common_tag[0]}' ({most_common_tag[1]} tasks)")

        # General productivity suggestions
        if analysis['incomplete'] > 20:
            suggestions.append("🗂️ Large task list detected. Consider breaking down or archiving completed tasks.")

        if not suggestions:
            suggestions.append("👍 Everything looks good! Keep up the great work.")

        return suggestions

    @staticmethod
    def get_next_recommended_tasks(state: AppState, limit: int = 3) -> List[Task]:
        """
        Recommend which tasks to work on next
        Based on priority and other factors
        """
        incomplete = [t for t in state.tasks if not t.done]

        if not incomplete:
            return []

        # Sort by priority (lower number = higher priority)
        # Then by ID (older tasks first)
        sorted_tasks = sorted(incomplete, key=lambda t: (t.priority, t.id))

        return sorted_tasks[:limit]

    @staticmethod
    def get_priority_distribution(state: AppState) -> str:
        """
        Get a visual representation of priority distribution
        """
        analysis = LocalSuggestions.analyze_tasks(state)

        high = analysis['high_priority_count']
        medium = analysis['medium_priority_count']
        low = analysis['low_priority_count']

        # Create a simple bar chart
        total_incomplete = high + medium + low
        if total_incomplete == 0:
            return "No incomplete tasks"

        high_bar = '█' * (high * 10 // max(total_incomplete, 1))
        medium_bar = '█' * (medium * 10 // max(total_incomplete, 1))
        low_bar = '█' * (low * 10 // max(total_incomplete, 1))

        return f"""
Priority Distribution (Incomplete Tasks):
  🔴 High   [{high:2d}]: {high_bar}
  🟡 Medium [{medium:2d}]: {medium_bar}
  🟢 Low    [{low:2d}]: {low_bar}
"""

    @staticmethod
    def get_tag_summary(state: AppState) -> str:
        """
        Get summary of tasks by tag
        """
        if not state.tasks:
            return "No tasks available"

        tags = {}
        for task in state.tasks:
            if task.tag:
                if task.tag not in tags:
                    tags[task.tag] = {'total': 0, 'done': 0}
                tags[task.tag]['total'] += 1
                if task.done:
                    tags[task.tag]['done'] += 1

        if not tags:
            return "No tags found"

        lines = ["\nTag Summary:"]
        for tag, counts in sorted(tags.items()):
            progress = counts['done'] / counts['total'] * 100 if counts['total'] > 0 else 0
            lines.append(f"  🏷️ {tag:15s} → {counts['done']}/{counts['total']} ({progress:.0f}%)")

        return '\n'.join(lines)

    @staticmethod
    def suggest_filter(state: AppState) -> List[Tuple[str, str]]:
        """
        Suggest useful filters based on current state
        Returns list of (filter_command, description) tuples
        """
        suggestions = []

        analysis = LocalSuggestions.analyze_tasks(state)

        # Suggest high priority filter if many high priority tasks
        if analysis['high_priority_count'] > 3:
            suggestions.append(("filter undone", "Focus on incomplete tasks"))

        # Suggest tag-specific filters
        if analysis['by_tag']:
            top_tags = sorted(analysis['by_tag'].items(), key=lambda x: x[1], reverse=True)[:3]
            for tag, count in top_tags:
                suggestions.append((f"filter tag:{tag}", f"View {count} {tag} tasks"))

        # Suggest completion filter
        if analysis['completed'] > 10:
            suggestions.append(("filter done", "Review completed tasks"))

        return suggestions

    @staticmethod
    def get_insights_summary(state: AppState) -> str:
        """
        Generate a comprehensive insights summary
        """
        analysis = LocalSuggestions.analyze_tasks(state)

        if not state.tasks:
            return "📊 No tasks to analyze. Add some tasks to get started!"

        lines = [
            "📊 Task Insights",
            "─" * 40,
            f"Total Tasks:     {analysis['total']}",
            f"Completed:       {analysis['completed']} ({analysis['completion_rate']:.1f}%)",
            f"Incomplete:      {analysis['incomplete']}",
            "",
            LocalSuggestions.get_priority_distribution(state),
        ]

        # Add tag summary if tags exist
        if analysis['by_tag']:
            lines.append(LocalSuggestions.get_tag_summary(state))

        # Add smart suggestions
        lines.append("\n💡 Smart Suggestions:")
        for suggestion in LocalSuggestions.get_smart_suggestions(state):
            lines.append(f"  {suggestion}")

        # Add recommended next tasks
        next_tasks = LocalSuggestions.get_next_recommended_tasks(state, limit=3)
        if next_tasks:
            lines.append("\n⚡ Recommended Next Tasks:")
            for i, task in enumerate(next_tasks, 1):
                priority_icon = "🔴" if task.priority == 1 else "🟡" if task.priority == 2 else "🟢"
                lines.append(f"  {i}. {priority_icon} [{task.id}] {task.name[:50]}")

        return '\n'.join(lines)

    @staticmethod
    def quick_stats(state: AppState) -> str:
        """
        Quick one-line stats for status bar
        """
        analysis = LocalSuggestions.analyze_tasks(state)
        return (f"📊 {analysis['total']} tasks | "
                f"✅ {analysis['completed']} done | "
                f"⚠️ {analysis['high_priority_count']} high priority | "
                f"{analysis['completion_rate']:.0f}% complete")
