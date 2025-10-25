"""
Local AI Suggestions - No OpenAI API required
Provides intelligent task insights and suggestions using local analysis
"""

from typing import List, Dict, Tuple, Any
from collections import Counter
from datetime import datetime
from models.task import Task
from core.state import AppState
from config import analysis, USE_UNICODE


class LocalSuggestions:
    """
    Provides intelligent suggestions without external API calls
    """

    @staticmethod
    def analyze_tasks(state: AppState) -> Dict[str, Any]:
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

        # Group by tag (use task.tags to support multi-tag)
        by_tag = Counter()
        for t in state.tasks:
            if not t.done:
                for tag in t.tags:  # Count all tags, not just first
                    by_tag[tag] += 1

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
            tip = "💡 Start by adding your first task with '/add' or 'add'" if USE_UNICODE else "Tip: Start by adding your first task with '/add' or 'add'"
            return [tip]

        suggestions = []
        task_analysis = LocalSuggestions.analyze_tasks(state)

        # Completion rate suggestions (using config thresholds)
        if task_analysis['completion_rate'] < analysis.LOW_COMPLETION_RATE_THRESHOLD:
            suggestions.append("🎯 Low completion rate detected. Focus on completing a few high-priority tasks." if USE_UNICODE else "Low completion rate detected. Focus on completing a few high-priority tasks.")
        elif task_analysis['completion_rate'] > analysis.HIGH_COMPLETION_RATE_THRESHOLD:
            suggestions.append("🎉 Great progress! You've completed most of your tasks." if USE_UNICODE else "Great progress! You've completed most of your tasks.")

        # Priority-based suggestions (using config threshold)
        if task_analysis['high_priority_count'] > analysis.HIGH_PRIORITY_WARNING_THRESHOLD:
            warning = "⚠️" if USE_UNICODE else "!"
            suggestions.append(f"{warning} You have {task_analysis['high_priority_count']} high-priority tasks. Consider focusing on these first.")

        if task_analysis['high_priority_count'] == 0 and task_analysis['incomplete'] > 0:
            suggestions.append("✨ No high-priority tasks! Start with medium priority items." if USE_UNICODE else "No high-priority tasks. Start with medium priority items.")

        # Tag-based suggestions
        if task_analysis['by_tag']:
            most_common_tag = max(task_analysis['by_tag'].items(), key=lambda x: x[1])
            emoji = "📊" if USE_UNICODE else "Stats:"
            suggestions.append(f"{emoji} Most active tag: '{most_common_tag[0]}' ({most_common_tag[1]} tasks)")

        # General productivity suggestions (using config threshold)
        if task_analysis['incomplete'] > analysis.LARGE_TASK_LIST_THRESHOLD:
            suggestions.append("🗂️ Large task list detected. Consider breaking down or archiving completed tasks." if USE_UNICODE else "Large task list detected. Consider breaking down or archiving completed tasks.")

        if not suggestions:
            suggestions.append("👍 Everything looks good! Keep up the great work." if USE_UNICODE else "Everything looks good! Keep up the great work.")

        return suggestions

    @staticmethod
    def get_next_recommended_tasks(state: AppState, limit: int = None) -> List[Task]:
        """
        Recommend which tasks to work on next
        Based on priority and other factors
        """
        if limit is None:
            limit = analysis.RECOMMENDED_TASKS_COUNT

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

        block = '█' if USE_UNICODE else '#'
        high_bar = block * (high * 10 // max(total_incomplete, 1))
        medium_bar = block * (medium * 10 // max(total_incomplete, 1))
        low_bar = block * (low * 10 // max(total_incomplete, 1))

        high_label = "🔴 High" if USE_UNICODE else "HIGH"
        med_label = "🟡 Medium" if USE_UNICODE else "MEDIUM"
        low_label = "🟢 Low" if USE_UNICODE else "LOW"

        return f"""
Priority Distribution (Incomplete Tasks):
  {high_label:10s} [{high:2d}]: {high_bar}
  {med_label:10s} [{medium:2d}]: {medium_bar}
  {low_label:10s} [{low:2d}]: {low_bar}
"""

    @staticmethod
    def get_tag_summary(state: AppState) -> str:
        """
        Get summary of tasks by tag
        Uses O(1) tag index for performance
        """
        if not state.tasks:
            return "No tasks available"

        # Use O(1) tag statistics instead of O(n) iteration
        tag_stats = state.get_all_tags_with_stats()

        if not tag_stats:
            return "No tags found"

        lines = ["\nTag Summary:"]
        for tag in sorted(tag_stats.keys()):
            stats = tag_stats[tag]
            progress = stats['done'] / stats['total'] * 100 if stats['total'] > 0 else 0
            lines.append(f"  🏷️ {tag:15s} → {stats['done']}/{stats['total']} ({progress:.0f}%)")

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
            return "📊 No tasks to analyze. Add some tasks to get started!" if USE_UNICODE else "No tasks to analyze. Add some tasks to get started!"

        title = "📊 Task Insights" if USE_UNICODE else "Task Insights"
        line_char = "─" if USE_UNICODE else "-"
        lines = [
            title,
            line_char * 40,
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
        lines.append("\n💡 Smart Suggestions:" if USE_UNICODE else "\nSuggestions:")
        for suggestion in LocalSuggestions.get_smart_suggestions(state):
            lines.append(f"  {suggestion}")

        # Add recommended next tasks
        next_tasks = LocalSuggestions.get_next_recommended_tasks(state, limit=3)
        if next_tasks:
            lines.append("\n⚡ Recommended Next Tasks:")
            for i, task in enumerate(next_tasks, 1):
                if USE_UNICODE:
                    priority_icon = "🔴" if task.priority == 1 else "🟡" if task.priority == 2 else "🟢"
                    lines.append(f"  {i}. {priority_icon} [{task.id}] {task.name[:50]}")
                else:
                    pr_label = "HIGH" if task.priority == 1 else "MED" if task.priority == 2 else "LOW"
                    lines.append(f"  {i}. {pr_label} [{task.id}] {task.name[:50]}")

        return '\n'.join(lines)

    @staticmethod
    def quick_stats(state: AppState) -> str:
        """
        Quick one-line stats for status bar
        """
        analysis = LocalSuggestions.analyze_tasks(state)
        return ((f"📊 {analysis['total']} tasks | " if USE_UNICODE else f"Tasks: {analysis['total']} | ")
                + (f"✅ {analysis['completed']} done | " if USE_UNICODE else f"Done: {analysis['completed']} | ")
                + (f"⚠️ {analysis['high_priority_count']} high priority | " if USE_UNICODE else f"High: {analysis['high_priority_count']} | ")
                + f"{analysis['completion_rate']:.0f}% complete")
