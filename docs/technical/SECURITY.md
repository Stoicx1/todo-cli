# Security Documentation

**Project:** Todo CLI Task Manager
**Version:** 2.0
**Last Updated:** 2025-10-21

---

## 🔒 Security Overview

This document outlines the security measures implemented in the Todo CLI application to protect against common vulnerabilities and ensure safe operation.

---

## 🛡️ Security Features

### 1. Input Validation & Sanitization

**Threat Mitigated:** Injection attacks, data corruption, buffer overflows

#### Task Name Validation
- **Max Length:** 200 characters
- **Min Length:** 1 character
- **Protection:** Prevents UI crashes from oversized inputs
- **Location:** `utils/validators.py::validate_task_name()`

```python
# Example
validate_task_name("x" * 1000)  # Returns: (False, "Task name too long")
```

#### Comment & Description Sanitization
- **Comment Max:** 500 characters
- **Description Max:** 2000 characters
- **Auto-truncation:** Yes (with warning)
- **Location:** `utils/validators.py::sanitize_comment()`, `sanitize_description()`

#### Tag Validation
- **Max Tags:** 3 per task
- **Allowed Characters:** Alphanumeric, hyphens, underscores
- **Format:** Lowercase, trimmed
- **Protection:** Prevents special character injection
- **Location:** `utils/tag_parser.py::parse_tags()`

```python
# Invalid tags rejected
parse_tags("valid, invalid@tag, good-tag")
# Result: ["valid", "good-tag"]  # @ symbol rejected
```

#### Priority Clamping
- **Range:** 1-3 (auto-corrected)
- **Protection:** Prevents invalid priority values
- **Location:** `utils/validators.py::clamp_priority()`

---

### 2. File Path Security

**Threat Mitigated:** Path traversal, arbitrary file access, symlink attacks

#### Filename Validation
- **Path Traversal Protection:** Blocks `../`, `..\` sequences
- **Null Byte Protection:** Rejects `\x00` characters
- **Reserved Names:** Blocks Windows reserved names (CON, PRN, AUX, etc.)
- **Invalid Characters:** Blocks `< > : " | ? *`
- **Length Limits:** Max 255 bytes (filename), 1024 bytes (full path)
- **Location:** `utils/file_validators.py::validate_filename()`

```python
# Examples of blocked filenames
validate_filename("../../../etc/passwd")  # Path traversal
validate_filename("CON.json")             # Windows reserved name
validate_filename("file<>name.json")      # Invalid characters
validate_filename("file\x00.json")        # Null byte injection
```

#### Safe File Path Resolution
- **Symlink Protection:** Resolves absolute paths
- **Directory Escape Detection:** Ensures files stay within target directory
- **Location:** `utils/file_validators.py::get_safe_filepath()`

```python
# Security check prevents escape
get_safe_filepath("./data", "../../etc/passwd")
# Result: (False, "", "Path escapes target directory")
```

---

### 3. File Safety Mechanisms

**Threat Mitigated:** Data loss, file corruption, concurrent access issues

#### File Locking
- **Library:** `portalocker`
- **Lock Type:** Exclusive (write), Shared (read)
- **Timeout:** 5 seconds (configurable)
- **Protection:** Prevents concurrent write corruption
- **Location:** `core/file_safety.py::SafeFileManager`

#### Atomic Writes
- **Method:** Write to temp file → fsync → atomic replace
- **Protection:** Prevents partial write corruption
- **Guarantee:** Original file never in inconsistent state

#### Automatic Backups
- **Backup Count:** 3 rotating backups
- **Format:** `.backup`, `.backup.1`, `.backup.2`
- **Auto-Recovery:** Attempts backups if main file corrupted
- **Protection:** Prevents data loss from corruption

---

### 4. Data Integrity

**Threat Mitigated:** Data corruption, invalid data structures

#### JSON Serialization
- **Method:** `dataclasses.asdict()` for Task objects
- **Validation:** Type-safe dataclass with `__post_init__` validation
- **Protection:** Ensures consistent data structure

#### Tag Index Synchronization
- **Automatic:** Updated on add, remove, edit operations
- **Consistency:** Verified on load with rebuild
- **Protection:** Prevents stale data from causing issues

---

## 🚨 Vulnerabilities NOT Addressed

The following security considerations are explicitly **not implemented**:

### 1. Encryption at Rest
- **Status:** NOT IMPLEMENTED
- **Risk:** Tasks stored in plaintext JSON
- **Mitigation:** Users should rely on OS-level encryption (BitLocker, FileVault, LUKS)
- **Reason:** Out of scope for local CLI tool

### 2. Authentication / Authorization
- **Status:** NOT IMPLEMENTED
- **Risk:** Any user with file system access can read/modify tasks
- **Mitigation:** Rely on OS file permissions
- **Reason:** Single-user local application

### 3. Network Security
- **Status:** NOT APPLICABLE
- **Risk:** N/A (no network functionality)
- **Note:** OpenAI API calls use HTTPS (handled by `requests` library)

### 4. Code Injection via GPT Responses
- **Status:** PARTIAL PROTECTION
- **Risk:** GPT responses displayed in Rich panels (could contain escape codes)
- **Mitigation:** Rich library handles most escape sequence sanitization
- **Recommendation:** Don't execute GPT suggestions blindly

---

## 🔍 Security Audit Checklist

### Input Validation
- [x] Task name length validated
- [x] Comments/descriptions truncated
- [x] Tags validated for format
- [x] Priority clamped to valid range
- [x] All user inputs sanitized

### File Security
- [x] Filename validation (path traversal, null bytes, reserved names)
- [x] File locking implemented
- [x] Atomic writes implemented
- [x] Backup/recovery implemented
- [x] Safe file path resolution

### Data Integrity
- [x] Type-safe dataclasses
- [x] Index synchronization
- [x] JSON serialization validation
- [x] Auto-migration for backward compatibility

### Error Handling
- [x] File lock timeouts handled gracefully
- [x] File corruption auto-recovery
- [x] Invalid input errors user-friendly
- [x] No sensitive data in error messages

---

## 📋 Security Best Practices

### For Users

1. **File Permissions**
   ```bash
   # Restrict tasks.json to owner only
   chmod 600 tasks.json  # Unix/Linux
   icacls tasks.json /inheritance:r /grant:r %USERNAME%:F  # Windows
   ```

2. **Backup Important Data**
   ```bash
   # Manual backup before major changes
   cp tasks.json tasks.json.manual-backup
   ```

3. **Don't Store Sensitive Information**
   - Avoid passwords, API keys, personal data in tasks
   - Use reference IDs instead of sensitive values

4. **Update Regularly**
   ```bash
   git pull origin main  # Stay updated with security fixes
   ```

### For Developers

1. **Always Validate User Input**
   ```python
   # Use validation utilities
   from utils.validators import validate_task_name
   is_valid, error = validate_task_name(user_input)
   if not is_valid:
       print(f"Error: {error}")
       return
   ```

2. **Use Safe File Operations**
   ```python
   # Use SafeFileManager for all file I/O
   from core.file_safety import SafeFileManager
   manager = SafeFileManager("tasks.json")
   manager.save_json_with_lock(data)
   ```

3. **Never Trust External Data**
   ```python
   # Even from JSON, validate structure
   task = Task(**task_data)  # Raises error if invalid
   ```

4. **Maintain Least Privilege**
   - Don't request admin/root privileges
   - Only access files explicitly specified by user
   - Don't write to system directories

---

## 🐛 Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Instead:**
1. Email: security@example.com (replace with actual contact)
2. Include: Description, reproduction steps, impact assessment
3. Allow: 90 days for patch before public disclosure
4. Expect: Acknowledgment within 48 hours

---

## 📜 Security Changelog

### Version 2.0 (2025-10-21)
- ✅ Added comprehensive filename validation
- ✅ Added input sanitization for all text fields
- ✅ Implemented tag validation with warnings
- ✅ Added file locking for concurrent access
- ✅ Implemented atomic writes
- ✅ Added automatic backup/recovery
- ✅ Fixed file descriptor leaks (Windows)
- ✅ Added path traversal protection

### Version 1.0 (Previous)
- ⚠️ Basic validation only
- ⚠️ No file locking
- ⚠️ No backup/recovery
- ⚠️ Partial input validation

---

## 🔗 Related Documentation

- **File Safety:** `FILE_SAFETY_COMPLETE.md`
- **Validation:** `utils/validators.py`, `utils/file_validators.py`
- **Implementation Details:** `COMPREHENSIVE_REVIEW_2025.md`

---

## ✅ Security Compliance

### OWASP Top 10 (Applicable Items)

1. **A01 - Broken Access Control**
   - ✅ Relies on OS file permissions
   - ✅ Filename validation prevents path traversal

2. **A03 - Injection**
   - ✅ Input validation on all fields
   - ✅ Tag format validation
   - ✅ No SQL (using JSON)
   - ✅ No shell execution (besides user's own commands)

3. **A04 - Insecure Design**
   - ✅ File safety by design
   - ✅ Defensive programming
   - ✅ Fail-safe defaults

4. **A05 - Security Misconfiguration**
   - ✅ Secure defaults (validation enabled)
   - ✅ No debug mode in production
   - ✅ Clear error messages without sensitive data

5. **A06 - Vulnerable Components**
   - ✅ Dependencies regularly updated
   - ✅ Using maintained libraries (rich, portalocker, questionary)

---

**Last Security Audit:** 2025-10-21
**Next Planned Audit:** TBD
**Security Contact:** TBD
