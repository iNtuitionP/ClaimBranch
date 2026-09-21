"""Bounded AppContainer experiment using ONLY freshly-created synthetic files.

No provider, production store, human-presence claim, receipt, network test, or
product runtime choice. Requires Windows and its existing .NET Framework C#
compiler. Creates/deletes only its unique per-run AppContainer profile. No
installation, existing-account changes, or global settings. Windows failures
are errors.
"""

import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import uuid


class ProbeError(RuntimeError):
    """The experiment did not establish its bounded guarantee."""


class UnsupportedPlatform(ProbeError):
    """AppContainer is available only on Windows."""


class _ChildTerminationError(ProbeError):
    """Own child may still be live; its files and profile must be preserved."""


def _temporary_root():
    root = Path(tempfile.gettempdir())
    if not root.is_absolute() or root == Path(root.anchor) or not root.is_dir() or root.resolve() != root:
        raise ProbeError("An existing normalized temporary root is required")
    for path in (root, *root.parents):
        if (path / ".git").exists() or path.is_symlink() or (
            getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ProbeError("Temporary root must be outside Git and reparse points")
    return root


class _Startup(C.Structure):
    _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR),
                ("title", W.LPWSTR), ("x", W.DWORD), ("y", W.DWORD),
                ("xsize", W.DWORD), ("ysize", W.DWORD), ("xchars", W.DWORD),
                ("ychars", W.DWORD), ("fill", W.DWORD), ("flags", W.DWORD),
                ("show", W.WORD), ("reserved_size", W.WORD), ("reserved2", C.c_void_p),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class _StartupEx(C.Structure):
    _fields_ = [("startup", _Startup), ("attributes", C.c_void_p)]


class _Process(C.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE),
                ("pid", W.DWORD), ("tid", W.DWORD)]


class _Capabilities(C.Structure):
    _fields_ = [("sid", C.c_void_p), ("capabilities", C.c_void_p),
                ("count", W.DWORD), ("reserved", W.DWORD)]


class _Windows:
    def __init__(self):
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        self.security = C.WinDLL("advapi32", use_last_error=True)
        self.userenv = C.WinDLL("userenv", use_last_error=True)
        self.ole = C.WinDLL("ole32", use_last_error=True)
        P = C.c_void_p
        self._bind(self.kernel, "GetCurrentProcess", [], W.HANDLE)
        self._bind(self.kernel, "GetSystemDirectoryW", [W.LPWSTR, W.UINT], W.UINT)
        self._bind(self.kernel, "CloseHandle", [W.HANDLE], W.BOOL)
        self._bind(self.kernel, "LocalFree", [P], P)
        self._bind(self.kernel, "InitializeProcThreadAttributeList", [P, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)], W.BOOL)
        self._bind(self.kernel, "UpdateProcThreadAttribute", [P, W.DWORD, C.c_size_t, P, C.c_size_t, P, P], W.BOOL)
        self._bind(self.kernel, "DeleteProcThreadAttributeList", [P], None)
        self._bind(self.kernel, "CreateProcessW", [W.LPCWSTR, W.LPWSTR, P, P, W.BOOL, W.DWORD, P, W.LPCWSTR, P, C.POINTER(_Process)], W.BOOL)
        self._bind(self.kernel, "ResumeThread", [W.HANDLE], W.DWORD)
        self._bind(self.kernel, "WaitForSingleObject", [W.HANDLE, W.DWORD], W.DWORD)
        self._bind(self.kernel, "TerminateProcess", [W.HANDLE, W.UINT], W.BOOL)
        self._bind(self.kernel, "GetExitCodeProcess", [W.HANDLE, C.POINTER(W.DWORD)], W.BOOL)
        self._bind(self.security, "OpenProcessToken", [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)], W.BOOL)
        self._bind(self.security, "GetTokenInformation", [W.HANDLE, C.c_int, P, W.DWORD, C.POINTER(W.DWORD)], W.BOOL)
        self._bind(self.security, "ConvertSidToStringSidW", [P, C.POINTER(W.LPWSTR)], W.BOOL)
        self._bind(self.security, "FreeSid", [P], P)
        self._bind(self.security, "ConvertStringSecurityDescriptorToSecurityDescriptorW", [W.LPCWSTR, W.DWORD, C.POINTER(P), P], W.BOOL)
        self._bind(self.security, "GetSecurityDescriptorDacl", [P, C.POINTER(W.BOOL), C.POINTER(P), C.POINTER(W.BOOL)], W.BOOL)
        self._bind(self.security, "GetSecurityDescriptorSacl", [P, C.POINTER(W.BOOL), C.POINTER(P), C.POINTER(W.BOOL)], W.BOOL)
        self._bind(self.security, "SetNamedSecurityInfoW", [W.LPWSTR, C.c_int, W.DWORD, P, P, P, P], W.DWORD)
        self._bind(self.userenv, "CreateAppContainerProfile", [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, P, W.DWORD, C.POINTER(P)], C.c_long)
        self._bind(self.userenv, "DeleteAppContainerProfile", [W.LPCWSTR], C.c_long)
        self._bind(self.userenv, "GetAppContainerFolderPath", [W.LPCWSTR, C.POINTER(W.LPWSTR)], C.c_long)
        self._bind(self.ole, "CoTaskMemFree", [P], None)

    @staticmethod
    def _bind(library, name, arguments, result):
        function = getattr(library, name)
        function.argtypes = arguments
        function.restype = result

    @staticmethod
    def require(ok, stage):
        if not ok:
            raise ProbeError(f"{stage} failed (Windows error {C.get_last_error()})")

    def token_info(self, process, kind):
        token = W.HANDLE()
        self.require(self.security.OpenProcessToken(process, 8, C.byref(token)), "OpenProcessToken")
        try:
            size = W.DWORD()
            self.security.GetTokenInformation(token, kind, None, 0, C.byref(size))
            data = C.create_string_buffer(size.value)
            self.require(self.security.GetTokenInformation(token, kind, data, size, C.byref(size)), "GetTokenInformation")
            return data
        finally:
            self.kernel.CloseHandle(token)

    def sid_text(self, sid):
        value = W.LPWSTR()
        self.require(self.security.ConvertSidToStringSidW(sid, C.byref(value)), "ConvertSidToStringSid")
        try:
            return value.value
        finally:
            self.kernel.LocalFree(value)

    def set_acl(self, path, owner, app_sid=None, writable=False):
        # Called only for exact objects freshly created by run_probe.
        sddl = f"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;{owner})"
        if app_sid:
            sddl += f"(A;{'OICI' if writable else ''};{'FA' if writable else 'FRFX'};;;{app_sid})"
        if writable:
            sddl += "S:(ML;OICI;NW;;;LW)"
        descriptor = C.c_void_p()
        self.require(self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(descriptor), None), "ConvertSecurityDescriptor")
        try:
            present, defaulted = W.BOOL(), W.BOOL()
            dacl, sacl = C.c_void_p(), C.c_void_p()
            self.require(self.security.GetSecurityDescriptorDacl(descriptor, C.byref(present), C.byref(dacl), C.byref(defaulted)), "GetDacl")
            if writable:
                self.require(self.security.GetSecurityDescriptorSacl(descriptor, C.byref(present), C.byref(sacl), C.byref(defaulted)), "GetLabel")
            code = self.security.SetNamedSecurityInfoW(str(path), 1, 0x80000004 | (0x10 if writable else 0), None, None, dacl, sacl)
            if code:
                raise ProbeError(f"Synthetic ACL setup failed (Windows error {code})")
        finally:
            self.kernel.LocalFree(descriptor)

    def launch(self, executable, root, sid=None):
        startup, process = _StartupEx(), _Process()
        startup.startup.cb = C.sizeof(startup)
        attributes = None
        running = False
        try:
            if sid:
                size = C.c_size_t()
                self.kernel.InitializeProcThreadAttributeList(None, 1, 0, C.byref(size))
                attributes = C.create_string_buffer(size.value)
                self.require(self.kernel.InitializeProcThreadAttributeList(attributes, 1, 0, C.byref(size)), "InitializeProcThreadAttributeList")
                startup.attributes = C.cast(attributes, C.c_void_p)
                capabilities = _Capabilities(sid, None, 0, 0)
                self.require(self.kernel.UpdateProcThreadAttribute(attributes, 0, 0x20009, C.byref(capabilities), C.sizeof(capabilities), None, None), "SetAppContainerCapabilities")
            # Do not inherit environment secrets or handles; no shell/profile.
            buffer = C.create_unicode_buffer(32768)
            length = self.kernel.GetSystemDirectoryW(buffer, len(buffer))
            self.require(0 < length < len(buffer), "GetSystemDirectory")
            system = Path(buffer.value).parent
            environment = C.create_unicode_buffer(f"LOCALAPPDATA={root / 'output'}\0SystemRoot={system}\0TEMP={root / 'output'}\0TMP={root / 'output'}\0\0")
            command = C.create_unicode_buffer(f'"{executable}"')
            self.require(self.kernel.CreateProcessW(str(executable), command, None, None, False,
                0x00080000 | 0x00000400 | 0x08000000 | 0x4, environment, str(root), C.byref(startup), C.byref(process)), "CreateProcess isolated" if sid else "CreateProcess control")
            running = True
            info = self.token_info(process.process, 29)  # TokenIsAppContainer
            actual_container = bool(C.cast(info, C.POINTER(W.DWORD)).contents.value)
            if actual_container != bool(sid):
                raise ProbeError("Child token does not match the requested isolation")
            if self.kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
                raise ProbeError("Child could not resume")
            wait = self.kernel.WaitForSingleObject(process.process, 15000)
            if wait != 0:
                raise ProbeError(f"Child wait failed or timed out (wait code {wait})")
            running = False
            code = W.DWORD()
            self.require(self.kernel.GetExitCodeProcess(process.process, C.byref(code)), "GetExitCodeProcess")
            if code.value:
                raise ProbeError(f"Child runtime failed (exit code {code.value})")
            return actual_container
        finally:
            termination_unconfirmed = False
            if running:
                self.kernel.TerminateProcess(process.process, 1)
                # Even a failed TerminateProcess can race with natural exit.
                # The signaled process handle, not the request, proves exit.
                termination_unconfirmed = self.kernel.WaitForSingleObject(process.process, 5000) != 0
            if process.thread:
                self.kernel.CloseHandle(process.thread)
            if process.process:
                self.kernel.CloseHandle(process.process)
            if startup.attributes:
                self.kernel.DeleteProcThreadAttributeList(startup.attributes)
            if termination_unconfirmed:
                raise _ChildTerminationError("Child termination not confirmed; preserve owned resources")


def _cleanup(root, temporary):
    if root.parent != temporary or not root.name.startswith("claimbranch-isolation-probe-"):
        raise ProbeError("Cleanup target no longer matches this probe's disposable root")
    for path in (root, *root.rglob("*")):
        if path.is_symlink() or (getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ProbeError("Cleanup refused an unexpected link; synthetic sandbox preserved")
    shutil.rmtree(root)


def run_probe():
    """Run two real children and return bounded evidence, cleaning only own files."""
    temporary = _temporary_root()  # reject user-controlled unsafe placement first
    if os.name != "nt":
        raise UnsupportedPlatform("AppContainer requires Windows")
    windows = _Windows()
    owner_info = windows.token_info(windows.kernel.GetCurrentProcess(), 1)
    owner = windows.sid_text(C.cast(owner_info, C.POINTER(C.c_void_p)).contents)
    sid = C.c_void_p()
    profile_name = "ClaimBranch.IsolationProbe." + uuid.uuid4().hex
    status = windows.userenv.CreateAppContainerProfile(
        profile_name, profile_name, "Disposable synthetic isolation probe", None, 0, C.byref(sid))
    if status < 0:
        # Never adopt or delete an existing profile, even on a name collision.
        raise ProbeError(f"Fresh AppContainer profile creation failed (HRESULT {status})")
    root = None
    profile_folder = None
    child_stopped = True
    try:
        app_sid = windows.sid_text(sid)
        folder = W.LPWSTR()
        folder_status = windows.userenv.GetAppContainerFolderPath(app_sid, C.byref(folder))
        if folder_status < 0:
            raise ProbeError(f"Own AppContainer folder lookup failed (HRESULT {folder_status})")
        try:
            profile_folder = Path(folder.value)
        finally:
            windows.ole.CoTaskMemFree(folder)
        root = Path(tempfile.mkdtemp(prefix="claimbranch-isolation-probe-", dir=temporary))
        windows.set_acl(root, owner, app_sid)
        output = root / "output"
        output.mkdir()
        windows.set_acl(output, owner, app_sid, writable=True)
        snapshots = {"accepted.bin": b"synthetic-accepted-original", "manuscript.tex": b"synthetic-manuscript-original",
                     "signing-secret.bin": b"synthetic-secret-not-a-signing-key"}
        for name, content in snapshots.items():
            target = root / name
            target.write_bytes(content)
            windows.set_acl(target, owner)
        buffer = C.create_unicode_buffer(32768)
        length = windows.kernel.GetSystemDirectoryW(buffer, len(buffer))
        windows.require(0 < length < len(buffer), "GetSystemDirectory")
        framework = "Framework64" if C.sizeof(C.c_void_p) == 8 else "Framework"
        compiler = Path(buffer.value).parent / "Microsoft.NET" / framework / "v4.0.30319" / "csc.exe"
        if not compiler.is_file():
            raise ProbeError("Existing .NET Framework C# compiler unavailable; nothing installed")
        source = root / "child.cs"
        shutil.copyfile(Path(__file__).with_name("windows_isolation_child.cs"), source)
        executable = root / "child.exe"
        compiled = subprocess.run([str(compiler), "/nologo", "/target:exe", "/out:" + str(executable), str(source)],
                                  cwd=root, capture_output=True, timeout=30, creationflags=0x08000000)
        if compiled.returncode:
            raise ProbeError(f"Synthetic helper compilation failed (exit code {compiled.returncode})")
        windows.set_acl(executable, owner, app_sid)
        keys = ("accepted_write", "manuscript_write", "secret_read", "proposal_write")
        observations = {}
        errors = {}
        for role, child_sid in (("control", None), ("isolated", sid)):
            container = windows.launch(executable, root, child_sid)
            report = output / "result.txt"
            if not report.is_file() or report.stat().st_size > 128:
                raise ProbeError(f"{role} child did not produce a bounded access report")
            try:
                codes = [int(value) for value in report.read_text().split(",")]
            except ValueError as exc:
                raise ProbeError("Child access report was invalid") from exc
            expected = [0, 0, 0, 0] if role == "control" else [5, 5, 5, 0]
            if codes != expected:
                raise ProbeError(f"{role} child access mismatch: {codes}; expected {expected}")
            if (output / "proposal.txt").read_bytes() != b"synthetic-proposal":
                raise ProbeError("Child did not write the synthetic proposal")
            observations[role] = {"appcontainer": container, **dict(zip(keys, (code == 0 for code in codes)))}
            errors[role] = dict(zip(keys, codes))
            if role == "control":
                for name, content in snapshots.items():
                    (root / name).write_bytes(content)
                report.unlink()
                (output / "proposal.txt").unlink()
        if any((root / name).read_bytes() != content for name, content in snapshots.items()):
            raise ProbeError("Isolated child changed protected synthetic content")
        result = {"status": "passed", "mechanism": "windows-appcontainer", **observations,
                  "access_errors": errors, "protected_unchanged": True}
    except _ChildTerminationError as exc:
        child_stopped = False
        raise ProbeError(f"Child termination not confirmed; owned profile={profile_name}; sandbox={root}; resources preserved") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError(f"Windows probe failed ({type(exc).__name__}); no isolation claim") from exc
    finally:
        windows.security.FreeSid(sid)
        if child_stopped:
            try:
                if root is not None:
                    try:
                        _cleanup(root, temporary)
                    except (OSError, ProbeError) as exc:
                        raise ProbeError(f"Own synthetic sandbox cleanup failed; sandbox={root}") from exc
            finally:
                status = windows.userenv.DeleteAppContainerProfile(profile_name)
                if status < 0:
                    raise ProbeError(f"Own AppContainer profile cleanup failed (HRESULT {status}); owned profile={profile_name}; sandbox={root}")
                if profile_folder is not None and profile_folder.exists():
                    raise ProbeError(f"Own AppContainer folder remains after deletion; owned profile={profile_name}; sandbox={root}")
    result["cleanup_complete"] = not root.exists()
    result["profile_cleanup_complete"] = True
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(run_probe(), sort_keys=True))
    except ProbeError as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        raise SystemExit(1)
