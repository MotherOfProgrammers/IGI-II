// Created By MotherOfProgrammers(MOP)

/*

Stage 0/1 proxy DLL for Project I.G.I. 2: Covert Strike (32-bit)
Loaded by the game as "version.dll" (placed next to igi2.exe)
It forwards the real VERSION.dll exports to the system copy, then patches igi2.exe's import table

(WSOCK32.dll + WININET.dll) so that we can:

1. LOG every hostname lookup, connect, bind, send/recv and sendto/recvfrom
(this is how we capture the master-server handshake and learn the protocol)

2. REDIRECT GameSpy/udpsoft hostnames to a master server of your choice

Nothing in igi2.exe is modified on disk
Delete version.dll to go back to stock
Build: see build.bat (MSVC x86  or  MinGW-w64 i686)
Config: igi2hook.ini next to the DLL
Log: igi2hook.log next to the DLL

*/

#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <winsock2.h>
#include <windows.h>
#include <wininet.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#ifdef _MSC_VER
#pragma comment(lib, "ws2_32.lib")
#endif

/*
VERSION.dll export forwarding
MSVC: done here with linker pragmas
MinGW: done by version.def (see build.bat)
*/

#ifdef _MSC_VER
#define FWD(name) __pragma(comment(linker, "/EXPORT:" #name "=C:\\Windows\\System32\\version." #name))
FWD(GetFileVersionInfoA)
FWD(GetFileVersionInfoByHandle)
FWD(GetFileVersionInfoExA)
FWD(GetFileVersionInfoExW)
FWD(GetFileVersionInfoSizeA)
FWD(GetFileVersionInfoSizeExA)
FWD(GetFileVersionInfoSizeExW)
FWD(GetFileVersionInfoSizeW)
FWD(GetFileVersionInfoW)
FWD(VerFindFileA)
FWD(VerFindFileW)
FWD(VerInstallFileA)
FWD(VerInstallFileW)
FWD(VerLanguageNameA)
FWD(VerLanguageNameW)
FWD(VerQueryValueA)
FWD(VerQueryValueW)
static void LoadRealVersionDll() {}
#else

// MinGW: each export is an asm stub that jumps through g_real[i], which is filled in
// at load time from the real C:\Windows\System32\version.dll
#define VER_EXPORTS(X)\
    X(0,  GetFileVersionInfoA) X(1,  GetFileVersionInfoByHandle) X(2,  GetFileVersionInfoExA)\
    X(3,  GetFileVersionInfoExW) X(4,  GetFileVersionInfoSizeA) X(5,  GetFileVersionInfoSizeExA)\
    X(6,  GetFileVersionInfoSizeExW) X(7,  GetFileVersionInfoSizeW) X(8,  GetFileVersionInfoW)\
    X(9,  VerFindFileA) X(10, VerFindFileW) X(11, VerInstallFileA) X(12, VerInstallFileW)\
    X(13, VerLanguageNameA) X(14, VerLanguageNameW) X(15, VerQueryValueA) X(16, VerQueryValueW)

extern "C" { void* g_real[17]; }

#define STUB(i, name) __asm__(".globl _" #name "\n_" #name ":\n\tjmp *_g_real+" #i "*4\n");
__asm__(".text");
VER_EXPORTS(STUB)

static void LoadRealVersionDll()
{
    static const char* names[17] = {
#define NAME(i, name) #name,
        VER_EXPORTS(NAME)
#undef NAME
    };
    char path[MAX_PATH + 16];
    GetSystemDirectoryA(path, MAX_PATH);
    strcat(path, "\\version.dll");
    HMODULE real = LoadLibraryA(path);
    if (!real) return;
    for (int i = 0; i < 17; ++i) g_real[i] = (void*)GetProcAddress(real, names[i]);
}
#endif


// Config
struct Config{
    int  enableRedirect; // 0 = log only, 1 = redirect matching hostnames
    char masterHost[256]; // hostname or dotted IP that matching names resolve to
    int  logBytes; // payload bytes to log per packet (0..256)
    int  udpLogMax; // max UDP packets to log (sendto/recvfrom)
    int  tcpLogMax; // max TCP send/recv to log
    int  forceEnctype0; // 1 = rewrite "\enctype\2\" -> "\enctype\0\" in outgoing TCP
    int  allowMulti; // 1 = allow several game instances (bypass "already running")
    int  heartbeat; // 1 = announce a hosted server to the master ourselves
    int  hostPort; // UDP port the game binds when hosting (IGI 2: 27900)
    int  masterUdpPort; // master's heartbeat port (UDP)
    int  heartbeatInterval; // seconds between heartbeats
    char gamename[64]; // GameSpy gamename sent in the heartbeat
};

static Config  g_cfg;
static char    g_pats[16][64];
static int     g_patCount = 0;
static char    g_dir[MAX_PATH] = "";


// Logging
static CRITICAL_SECTION g_lock;
static HANDLE           g_log = INVALID_HANDLE_VALUE;
static volatile LONG    g_udpCount = 0;
static volatile LONG    g_tcpCount = 0;

static void Log(const char* fmt, ...){
    if (g_log == INVALID_HANDLE_VALUE) return;

    char buf[2048];
    SYSTEMTIME st;
    GetLocalTime(&st);
    int n = snprintf(buf, sizeof(buf), "[%02d:%02d:%02d.%03d T%04lu] ",st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,(unsigned long)GetCurrentThreadId());
    if (n < 0) return;

    va_list ap;
    va_start(ap, fmt);
    int m = vsnprintf(buf + n, sizeof(buf) - (size_t)n - 3, fmt, ap);
    va_end(ap);
    if (m < 0) m = 0;
    n += m;
    if (n > (int)sizeof(buf) - 3) n = (int)sizeof(buf) - 3;
    buf[n++] = '\r';
    buf[n++] = '\n';

    EnterCriticalSection(&g_lock);
    DWORD written = 0;
    WriteFile(g_log, buf, (DWORD)n, &written, NULL);
    LeaveCriticalSection(&g_lock);
}

static void LogPayload(const char* tag, const char* peer, const char* data, int len){
    if (len <= 0 || g_cfg.logBytes <= 0 || !data) return;

    int n = len < g_cfg.logBytes ? len : g_cfg.logBytes;
    char ascii[260];
    bool binary = false;
    for (int i = 0; i < n; ++i){
        unsigned char c = (unsigned char)data[i];
        if (c >= 32 && c < 127){
            ascii[i] = (char)c;
        } else{
            ascii[i] = '.';
            if (c != '\r' && c != '\n') binary = true;
        }
    }
    ascii[n] = 0;

    Log("%s %s %d bytes: %s%s", tag, peer, len, ascii, n < len ? " ..." : "");

    if (binary){
        int m = n < 48 ? n : 48;
        char hex[3 * 48 + 1];
        for (int i = 0; i < m; ++i)
            snprintf(hex + 3 * i, 4, "%02X ", (unsigned char)data[i]);
        hex[3 * m] = 0;
        Log("    hex: %s", hex);
    }
}

static void FmtAddr(const struct sockaddr* sa, char* out, size_t cap){
    if (sa && sa->sa_family == AF_INET){
        const struct sockaddr_in* in = (const struct sockaddr_in*)sa;
        const unsigned char* b = (const unsigned char*)&in->sin_addr;
        unsigned port = (unsigned)(((in->sin_port & 0xFF) << 8) | ((in->sin_port >> 8) & 0xFF));
        snprintf(out, cap, "%u.%u.%u.%u:%u", b[0], b[1], b[2], b[3], port);
    } else{
        snprintf(out, cap, "family=%d", sa ? (int)sa->sa_family : -1);
    }
}

// Preserve the thread's last-error across our logging (WSAGetLastError == GetLastError)
struct ErrKeeper{
    DWORD e;
    ErrKeeper() : e(GetLastError()) {}
    ~ErrKeeper() { SetLastError(e); }
};


// Hostname matching
static bool MatchesPattern(const char* name){
    if (!name || !*name) return false;
    char lower[256];
    size_t i = 0;
    for (; name[i] && i < sizeof(lower) - 1; ++i)
        lower[i] = (char)tolower((unsigned char)name[i]);
    lower[i] = 0;

    for (int p = 0; p < g_patCount; ++p)
        if (g_pats[p][0] && strstr(lower, g_pats[p])) return true;
    return false;
}


// master_host=local -> the PC's current LAN address, learned from the game's own lookup of its computer name
// And the game ignores 127.0.0.1 masters, and a DHCP address can change between sessions, so a hard-coded LAN IP in the ini goes stale
static char g_localIp[32] = "";

static const char* MasterHostEff(){
    if (_stricmp(g_cfg.masterHost, "local") == 0)
        return g_localIp[0] ? g_localIp : "127.0.0.1";
    return g_cfg.masterHost;
}

// Hooks
typedef struct hostent* (WSAAPI* PFN_gethostbyname)(const char*);
typedef int (WSAAPI* PFN_connect)(SOCKET, const struct sockaddr*, int);
typedef int (WSAAPI* PFN_bind)(SOCKET, const struct sockaddr*, int);
typedef int (WSAAPI* PFN_send)(SOCKET, const char*, int, int);
typedef int (WSAAPI* PFN_recv)(SOCKET, char*, int, int);
typedef int (WSAAPI* PFN_sendto)(SOCKET, const char*, int, int, const struct sockaddr*, int);
typedef int (WSAAPI* PFN_recvfrom)(SOCKET, char*, int, int, struct sockaddr*, int*);
typedef HINTERNET (WINAPI* PFN_InternetOpenUrlA)(HINTERNET, LPCSTR, LPCSTR, DWORD, DWORD, DWORD_PTR);

static PFN_gethostbyname    real_gethostbyname    = NULL;
static PFN_connect          real_connect          = NULL;
static PFN_bind             real_bind             = NULL;
static PFN_send             real_send             = NULL;
static PFN_recv             real_recv             = NULL;
static PFN_sendto           real_sendto           = NULL;
static PFN_recvfrom         real_recvfrom         = NULL;
static PFN_InternetOpenUrlA real_InternetOpenUrlA = NULL;

static struct hostent* WSAAPI hk_gethostbyname(const char* name){
    const char* target = name;
    bool redirected = false;
    if (g_cfg.enableRedirect && g_cfg.masterHost[0] && MatchesPattern(name)){
        target = MasterHostEff();
        redirected = true;
    }

    struct hostent* h = real_gethostbyname(target);
    ErrKeeper keep;

    char ip[32] = "(failed)";
    if (h && h->h_addrtype == AF_INET && h->h_addr_list && h->h_addr_list[0]){
        const unsigned char* b = (const unsigned char*)h->h_addr_list[0];
        snprintf(ip, sizeof(ip), "%u.%u.%u.%u", b[0], b[1], b[2], b[3]);
    }
    if (!redirected && name && !strchr(name, '.') && !g_localIp[0] && ip[0] != '(')
        snprintf(g_localIp, sizeof(g_localIp), "%s", ip);   // the game looking up its own PC
    if (redirected)
        Log("gethostbyname(\"%s\") REDIRECTED to \"%s\" -> %s", name ? name : "(null)", target, ip);
    else
        Log("gethostbyname(\"%s\") -> %s", name ? name : "(null)", ip);
    return h;
}

static int WSAAPI hk_connect(SOCKET s, const struct sockaddr* name, int namelen){
    int r = real_connect(s, name, namelen);
    ErrKeeper keep;
    char a[64];
    FmtAddr(name, a, sizeof(a));
    Log("connect(%s) -> %d (err %lu)", a, r, keep.e);
    return r;
}

static volatile LONG g_hbStarted = 0;
static volatile int  g_hbPort = 0; // the port being announced

/*
Announces this machine's hosted game to the master
Runs inside the game process, so the master sees the host's real public IP as the packet source.
Uses our own ws2_32 import, which is not hooked
*/
static DWORD WINAPI HeartbeatThread(LPVOID){
    char msg[200];
    int n = snprintf(msg, sizeof(msg), "\\heartbeat\\%d\\gamename\\%s",
                     g_hbPort, g_cfg.gamename);
    Log("heartbeat thread started: \"%s\" every %d s to %s:%d", msg,
        g_cfg.heartbeatInterval, MasterHostEff(), g_cfg.masterUdpPort);
    for (;;){
        if (!g_cfg.masterHost[0]){
            Log("heartbeat: master_host is empty, nothing to announce to");
        } else{
            struct sockaddr_in to;
            memset(&to, 0, sizeof(to));
            to.sin_family = AF_INET;
            to.sin_port = htons((u_short)g_cfg.masterUdpPort);
            to.sin_addr.s_addr = inet_addr(MasterHostEff());
            if (to.sin_addr.s_addr == INADDR_NONE){
                struct hostent* h = gethostbyname(MasterHostEff());
                if (h && h->h_addrtype == AF_INET && h->h_addr_list && h->h_addr_list[0])
                    memcpy(&to.sin_addr, h->h_addr_list[0], 4);
            }
            if (to.sin_addr.s_addr == INADDR_NONE){
                Log("heartbeat: cannot resolve master_host \"%s\"", MasterHostEff());
            } else{
                SOCKET s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
                if (s != INVALID_SOCKET){
                    int r = sendto(s, msg, n, 0, (struct sockaddr*)&to, (int)sizeof(to));
                    int err = WSAGetLastError();
                    closesocket(s);
                    Log("heartbeat -> %s:%d (%d bytes, result %d, err %d)",
                        MasterHostEff(), g_cfg.masterUdpPort, n, r, err);
                }
            }
        }
        Sleep((DWORD)g_cfg.heartbeatInterval * 1000);
    }
    return 0;
}

static int WSAAPI hk_bind(SOCKET s, const struct sockaddr* name, int namelen){
    int r = real_bind(s, name, namelen);
    ErrKeeper keep;
    char a[64];
    FmtAddr(name, a, sizeof(a));
    Log("bind(%s) -> %d (err %lu)", a, r, keep.e);

    if (r == 0 && g_cfg.heartbeat && name && name->sa_family == AF_INET){
        const struct sockaddr_in* in = (const struct sockaddr_in*)name;
        int port = (int)ntohs(in->sin_port);
        // host_port=0 -> auto: the first explicit UDP bind (>=1024) is the hosted server.
        bool match = g_cfg.hostPort?(port == g_cfg.hostPort):(port >= 1024);
        if (match && InterlockedCompareExchange(&g_hbStarted, 1, 0) == 0){
            g_hbPort = port;
            Log("game bound host port %d: starting heartbeat", port);
            HANDLE t = CreateThread(NULL, 0, HeartbeatThread, NULL, 0, NULL);
            if (t) CloseHandle(t);
        }
    }
    return r;
}

// Same-length rewrite of the list-encryption request so our own master can answer in
// plain text.  Returns true if the buffer was changed.
static bool RewriteEnctype(char* b, int len){
    static const char pat[] = "\\enctype\\2\\";
    const int pl = (int)sizeof(pat) - 1;
    for (int i = 0; i + pl <= len; ++i){
        if (memcmp(b + i, pat, (size_t)pl) == 0){
            b[i + 9] = '0';     // pat = \ e n c t y p e \ 2 \  -> the '2' is index 9
            return true;
        }
    }
    return false;
}

static int WSAAPI hk_send(SOCKET s, const char* buf, int len, int flags){
    char rewritten[1024];
    if (g_cfg.forceEnctype0 && len > 0 && len < (int)sizeof(rewritten)){
        memcpy(rewritten, buf, (size_t)len);
        if (RewriteEnctype(rewritten, len)){
            buf = rewritten;
            Log("send: rewrote \\enctype\\2\\ -> \\enctype\\0\\");
        }
    }
    int r = real_send(s, buf, len, flags);
    ErrKeeper keep;
    if (r > 0){
        LONG c = InterlockedIncrement(&g_tcpCount);
        if (c <= g_cfg.tcpLogMax) LogPayload("TCP send", "", buf, r);
        else if (c == g_cfg.tcpLogMax + 1) Log("(TCP logging limit reached)");
    }
    return r;
}

static int WSAAPI hk_recv(SOCKET s, char* buf, int len, int flags){
    int r = real_recv(s, buf, len, flags);
    ErrKeeper keep;
    if (r > 0) {
        LONG c = InterlockedIncrement(&g_tcpCount);
        if (c <= g_cfg.tcpLogMax) LogPayload("TCP recv", "", buf, r);
        else if (c == g_cfg.tcpLogMax + 1) Log("(TCP logging limit reached)");
    }
    return r;
}

static int WSAAPI hk_sendto(SOCKET s, const char* buf, int len, int flags,const struct sockaddr* to, int tolen){
    int r = real_sendto(s, buf, len, flags, to, tolen);
    ErrKeeper keep;
    if (r > 0){
        LONG c = InterlockedIncrement(&g_udpCount);
        if (c <= g_cfg.udpLogMax){
            char a[64];
            FmtAddr(to, a, sizeof(a));
            LogPayload("UDP sendto", a, buf, r);
        } else if (c == g_cfg.udpLogMax + 1){
            Log("(UDP logging limit reached)");
        }
    }
    return r;
}

static int WSAAPI hk_recvfrom(SOCKET s, char* buf, int len, int flags,struct sockaddr* from, int* fromlen){
    int r = real_recvfrom(s, buf, len, flags, from, fromlen);
    ErrKeeper keep;
    if (r > 0) {
        LONG c = InterlockedIncrement(&g_udpCount);
        if (c <= g_cfg.udpLogMax){
            char a[64];
            FmtAddr(from, a, sizeof(a));
            LogPayload("UDP recvfrom", a, buf, r);
        } else if (c == g_cfg.udpLogMax + 1){
            Log("(UDP logging limit reached)");
        }
    }
    return r;
}

static HINTERNET WINAPI hk_InternetOpenUrlA(HINTERNET hInet, LPCSTR url, LPCSTR hdrs,DWORD hdrLen, DWORD flags, DWORD_PTR ctx){
    Log("InternetOpenUrlA(\"%s\")", url ? url : "(null)");
    return real_InternetOpenUrlA(hInet, url, hdrs, hdrLen, flags, ctx);
}

/*
Single-instance bypass (allow_multi=1) -> "innerloop game is already running"
Named kernel objects (mutex/event/semaphore/file mapping) get the process id
appended so every game process creates its own FindWindow results that belong to another process are hidden
All calls are logged so we can see which one the game uses
*/

typedef HANDLE (WINAPI *PFN_CreateMutexA)(LPSECURITY_ATTRIBUTES, BOOL, LPCSTR);
typedef HANDLE (WINAPI *PFN_CreateMutexW)(LPSECURITY_ATTRIBUTES, BOOL, LPCWSTR);
typedef HANDLE (WINAPI *PFN_OpenMutexA)(DWORD, BOOL, LPCSTR);
typedef HANDLE (WINAPI *PFN_OpenMutexW)(DWORD, BOOL, LPCWSTR);
typedef HANDLE (WINAPI *PFN_CreateEventA)(LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCSTR);
typedef HANDLE (WINAPI *PFN_CreateEventW)(LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR);
typedef HANDLE (WINAPI *PFN_CreateSemaphoreA)(LPSECURITY_ATTRIBUTES, LONG, LONG, LPCSTR);
typedef HANDLE (WINAPI *PFN_CreateSemaphoreW)(LPSECURITY_ATTRIBUTES, LONG, LONG, LPCWSTR);
typedef HANDLE (WINAPI *PFN_CreateFileMappingA)(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCSTR);
typedef HANDLE (WINAPI *PFN_CreateFileMappingW)(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCWSTR);
typedef HWND   (WINAPI *PFN_FindWindowA)(LPCSTR, LPCSTR);
typedef HWND   (WINAPI *PFN_FindWindowW)(LPCWSTR, LPCWSTR);

static PFN_CreateMutexA       real_CreateMutexA = NULL;
static PFN_CreateMutexW       real_CreateMutexW = NULL;
static PFN_OpenMutexA         real_OpenMutexA = NULL;
static PFN_OpenMutexW         real_OpenMutexW = NULL;
static PFN_CreateEventA       real_CreateEventA = NULL;
static PFN_CreateEventW       real_CreateEventW = NULL;
static PFN_CreateSemaphoreA   real_CreateSemaphoreA = NULL;
static PFN_CreateSemaphoreW   real_CreateSemaphoreW = NULL;
static PFN_CreateFileMappingA real_CreateFileMappingA = NULL;
static PFN_CreateFileMappingW real_CreateFileMappingW = NULL;
static PFN_FindWindowA        real_FindWindowA = NULL;
static PFN_FindWindowW        real_FindWindowW = NULL;

// Returns the name to really use (a per-process copy in buf when allow_multi is on)
static const char* UniqueNameA(const char* api, const char* name, char* buf, size_t cap){
    if (!name) return name;
    if (!g_cfg.allowMulti){Log("%s(\"%s\")", api, name); return name;}
    snprintf(buf, cap, "%s_p%lu", name, (unsigned long)GetCurrentProcessId());
    Log("%s(\"%s\") -> \"%s\"", api, name, buf);
    return buf;
}

static const wchar_t* UniqueNameW(const char* api, const wchar_t* name, wchar_t* buf, size_t cap){
    if (!name) return name;
    if (!g_cfg.allowMulti){Log("%s(\"%ls\")", api, name); return name;}
    _snwprintf(buf, cap, L"%ls_p%lu", name, (unsigned long)GetCurrentProcessId());
    buf[cap - 1] = 0;
    Log("%s(\"%ls\") -> \"%ls\"", api, name, buf);
    return buf;
}


static HANDLE WINAPI hk_CreateMutexA(LPSECURITY_ATTRIBUTES sa, BOOL own, LPCSTR name){
    char nb[300];
    name = UniqueNameA("CreateMutexA", name, nb, sizeof(nb));
    return real_CreateMutexA(sa, own, name);
}

static HANDLE WINAPI hk_CreateMutexW(LPSECURITY_ATTRIBUTES sa, BOOL own, LPCWSTR name){
    wchar_t nb[300];
    name = UniqueNameW("CreateMutexW", name, nb, 300);
    return real_CreateMutexW(sa, own, name);
}

static HANDLE WINAPI hk_OpenMutexA(DWORD acc, BOOL inh, LPCSTR name){
    char nb[300];
    name = UniqueNameA("OpenMutexA", name, nb, sizeof(nb));
    return real_OpenMutexA(acc, inh, name);
}

static HANDLE WINAPI hk_OpenMutexW(DWORD acc, BOOL inh, LPCWSTR name){
    wchar_t nb[300];
    name = UniqueNameW("OpenMutexW", name, nb, 300);
    return real_OpenMutexW(acc, inh, name);
}

static HANDLE WINAPI hk_CreateEventA(LPSECURITY_ATTRIBUTES sa, BOOL man, BOOL init, LPCSTR name){
    char nb[300];
    name = UniqueNameA("CreateEventA", name, nb, sizeof(nb));
    return real_CreateEventA(sa, man, init, name);
}

static HANDLE WINAPI hk_CreateEventW(LPSECURITY_ATTRIBUTES sa, BOOL man, BOOL init, LPCWSTR name){
    wchar_t nb[300];
    name = UniqueNameW("CreateEventW", name, nb, 300);
    return real_CreateEventW(sa, man, init, name);
}

static HANDLE WINAPI hk_CreateSemaphoreA(LPSECURITY_ATTRIBUTES sa, LONG i, LONG m, LPCSTR name){
    char nb[300];
    name = UniqueNameA("CreateSemaphoreA", name, nb, sizeof(nb));
    return real_CreateSemaphoreA(sa, i, m, name);
}

static HANDLE WINAPI hk_CreateSemaphoreW(LPSECURITY_ATTRIBUTES sa, LONG i, LONG m, LPCWSTR name){
    wchar_t nb[300];
    name = UniqueNameW("CreateSemaphoreW", name, nb, 300);
    return real_CreateSemaphoreW(sa, i, m, name);
}

static HANDLE WINAPI hk_CreateFileMappingA(HANDLE f, LPSECURITY_ATTRIBUTES sa, DWORD p, DWORD hi, DWORD lo, LPCSTR name){
    char nb[300];
    name = UniqueNameA("CreateFileMappingA", name, nb, sizeof(nb));
    return real_CreateFileMappingA(f, sa, p, hi, lo, name);
}

static HANDLE WINAPI hk_CreateFileMappingW(HANDLE f, LPSECURITY_ATTRIBUTES sa, DWORD p, DWORD hi, DWORD lo, LPCWSTR name){
    wchar_t nb[300];
    name = UniqueNameW("CreateFileMappingW", name, nb, 300);
    return real_CreateFileMappingW(f, sa, p, hi, lo, name);
}

static HWND WINAPI hk_FindWindowA(LPCSTR cls, LPCSTR title){
    HWND h = real_FindWindowA(cls, title);
    DWORD pid = 0;
    if (h) GetWindowThreadProcessId(h, &pid);
    Log("FindWindowA(\"%s\", \"%s\") -> %p (pid %lu)", cls?cls:"(null)", title?title:"(null)",
        (void*)h, (unsigned long)pid);
    if (h && g_cfg.allowMulti && pid != GetCurrentProcessId()){SetLastError(0); return NULL;}
    return h;
}

static HWND WINAPI hk_FindWindowW(LPCWSTR cls, LPCWSTR title){
    HWND h = real_FindWindowW(cls, title);
    DWORD pid = 0;
    if (h) GetWindowThreadProcessId(h, &pid);
    Log("FindWindowW(\"%ls\", \"%ls\") -> %p (pid %lu)", cls?cls:L"(null)",title?title:L"(null)",
        (void*)h, (unsigned long)pid);
    if (h && g_cfg.allowMulti && pid != GetCurrentProcessId()){SetLastError(0);return NULL;}
    return h;
}


// Import-table patching
struct HookDef{
    const char* dll;
    const char* func;
    void*       hook;
    void**      orig;
    bool        patched;
    bool        optional; // not an error if the exe does not import it
};

static HookDef g_hooks[] = {
    { "WSOCK32.dll", "gethostbyname", (void*)hk_gethostbyname, (void**)&real_gethostbyname, false },
    { "WSOCK32.dll", "connect",       (void*)hk_connect,       (void**)&real_connect,       false },
    { "WSOCK32.dll", "bind",          (void*)hk_bind,          (void**)&real_bind,          false },
    { "WSOCK32.dll", "send",          (void*)hk_send,          (void**)&real_send,          false },
    { "WSOCK32.dll", "recv",          (void*)hk_recv,          (void**)&real_recv,          false },
    { "WSOCK32.dll", "sendto",        (void*)hk_sendto,        (void**)&real_sendto,        false },
    { "WSOCK32.dll", "recvfrom",      (void*)hk_recvfrom,      (void**)&real_recvfrom,      false },
    { "WININET.dll", "InternetOpenUrlA", (void*)hk_InternetOpenUrlA, (void**)&real_InternetOpenUrlA, false },
    // optional: single-instance checks
    { "KERNEL32.dll", "CreateMutexA",       (void*)hk_CreateMutexA,       (void**)&real_CreateMutexA,       false, true },
    { "KERNEL32.dll", "CreateMutexW",       (void*)hk_CreateMutexW,       (void**)&real_CreateMutexW,       false, true },
    { "KERNEL32.dll", "OpenMutexA",         (void*)hk_OpenMutexA,         (void**)&real_OpenMutexA,         false, true },
    { "KERNEL32.dll", "OpenMutexW",         (void*)hk_OpenMutexW,         (void**)&real_OpenMutexW,         false, true },
    { "KERNEL32.dll", "CreateEventA",       (void*)hk_CreateEventA,       (void**)&real_CreateEventA,       false, true },
    { "KERNEL32.dll", "CreateEventW",       (void*)hk_CreateEventW,       (void**)&real_CreateEventW,       false, true },
    { "KERNEL32.dll", "CreateSemaphoreA",   (void*)hk_CreateSemaphoreA,   (void**)&real_CreateSemaphoreA,   false, true },
    { "KERNEL32.dll", "CreateSemaphoreW",   (void*)hk_CreateSemaphoreW,   (void**)&real_CreateSemaphoreW,   false, true },
    { "KERNEL32.dll", "CreateFileMappingA", (void*)hk_CreateFileMappingA, (void**)&real_CreateFileMappingA, false, true },
    { "KERNEL32.dll", "CreateFileMappingW", (void*)hk_CreateFileMappingW, (void**)&real_CreateFileMappingW, false, true },
    { "USER32.dll",   "FindWindowA",        (void*)hk_FindWindowA,        (void**)&real_FindWindowA,        false, true },
    { "USER32.dll",   "FindWindowW",        (void*)hk_FindWindowW,        (void**)&real_FindWindowW,        false, true },
};


static const int HOOK_COUNT = (int)(sizeof(g_hooks) / sizeof(g_hooks[0]));

static void* ResolveExport(const char* dll, const char* func){
    HMODULE m = GetModuleHandleA(dll);
    if (!m) m = LoadLibraryA(dll);
    return m ? (void*)GetProcAddress(m, func):NULL;
}

/*
Patches by ADDRESS, not by name
Any IAT slot in the exe whose value equals the real function address gets replaced
This works for imports by name AND by ordinal,
and it only fires once the Windows loader has filled the IAT (before that, slots hold RVAs that can never equal a real function address)
*/
static bool PatchImport(HMODULE mod, HookDef& h){
    void* cand[2] = {ResolveExport(h.dll, h.func), NULL};
    if (_stricmp(h.dll, "WSOCK32.dll") == 0) cand[1] = ResolveExport("ws2_32.dll", h.func);
    if (!cand[0] && !cand[1]) return false;

    BYTE* base = (BYTE*)mod;
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return false;
    IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return false;

    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return false;

    IMAGE_IMPORT_DESCRIPTOR* d = (IMAGE_IMPORT_DESCRIPTOR*)(base + dir.VirtualAddress);
    for (; d->Name; ++d){
        IMAGE_THUNK_DATA* slots = (IMAGE_THUNK_DATA*)(base + d->FirstThunk);
        for (; slots->u1.Function; ++slots) {
            void** slot = (void**)&slots->u1.Function;
            if (*slot == h.hook) return true; // already patched
            if (*slot != cand[0] && *slot != cand[1]) continue;

            DWORD oldProt = 0;
            if (!VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &oldProt)) return false;
            *h.orig = *slot;
            *slot   = h.hook;
            VirtualProtect(slot, sizeof(void*), oldProt, &oldProt);
            return true;
        }
    }
    return false;
}

static bool ContainsNoCase(const char* hay, const char* needle){
    size_t n = strlen(needle);
    for (; *hay; ++hay)
        if (_strnicmp(hay, needle, n) == 0) return true;
    return false;
}

// Diagnostic
// list the exe's import DLLs, and every entry of socket-related ones
static void DumpImports(){
    BYTE* base = (BYTE*)GetModuleHandleA(NULL);
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress){Log("exe has no import directory");return;}

    IMAGE_IMPORT_DESCRIPTOR* d = (IMAGE_IMPORT_DESCRIPTOR*)(base + dir.VirtualAddress);
    for (; d->Name; ++d){
        const char* dll = (const char*)(base + d->Name);
        Log("exe imports DLL: %s", dll);
        if (!ContainsNoCase(dll, "sock") && !ContainsNoCase(dll, "inet")) continue;

        DWORD rva = d->OriginalFirstThunk ? d->OriginalFirstThunk : d->FirstThunk;
        IMAGE_THUNK_DATA* t = (IMAGE_THUNK_DATA*)(base + rva);
        for (; t->u1.AddressOfData; ++t){
            if (IMAGE_SNAP_BY_ORDINAL(t->u1.Ordinal))
                Log("    ordinal %lu", (unsigned long)IMAGE_ORDINAL(t->u1.Ordinal));
            else
                Log("    %s", (const char*)((IMAGE_IMPORT_BY_NAME*)(base + t->u1.AddressOfData))->Name);
        }
    }
}

// Returns the number of REQUIRED hooks installed (optional ones are tried in the same pass)
static int ApplyHooks(){
    HMODULE exe = GetModuleHandleA(NULL);
    int patched = 0;
    for (int i = 0; i < HOOK_COUNT; ++i){
        if (!g_hooks[i].patched && PatchImport(exe, g_hooks[i])){
            g_hooks[i].patched = true;
            Log("hooked %s!%s", g_hooks[i].dll, g_hooks[i].func);
        }
        if (g_hooks[i].patched && !g_hooks[i].optional) ++patched;
    }
    return patched;
}

static int RequiredHookCount(){
    int n = 0;
    for (int i = 0; i < HOOK_COUNT; ++i) if (!g_hooks[i].optional) ++n;
    return n;
}

/*
The loader fills the exe's import table only after all DLLs (including this one) have 
been loaded, so hook installation is done from a background thread that polls until
every hook is in (or ~15 s have passed)

Poll fast at first cause the single-instance check runs at the very start of the game,
so the import table must be patched the moment the loader has filled it
*/
static DWORD WINAPI RetryThread(LPVOID){
    const int need = RequiredHookCount();
    for (int i = 0; i < 340; ++i){
        if (ApplyHooks() == need) break;
        Sleep(i < 300 ? 1 : 250);
    }
    DumpImports();
    int ok = 0, req = 0;
    for (int i = 0; i < HOOK_COUNT; ++i){
        if (g_hooks[i].patched){++ok;continue;}
        if (g_hooks[i].optional)Log("not imported by the exe (optional): %s!%s", g_hooks[i].dll, g_hooks[i].func);
        else{++req; Log("NOT FOUND in exe imports: %s!%s", g_hooks[i].dll, g_hooks[i].func);}
    }
    Log("hook summary: %d/%d installed (%d required missing), allow_multi=%d",
        ok, HOOK_COUNT, req, g_cfg.allowMulti);
    return 0;
}


// Startup
static void LoadConfig(HINSTANCE self){
    char path[MAX_PATH] = "";
    GetModuleFileNameA(self, path, MAX_PATH);
    char* slash = strrchr(path, '\\');
    if (slash) *slash = 0;
    snprintf(g_dir, sizeof(g_dir), "%s", path);

    char ini[MAX_PATH + 32];
    snprintf(ini, sizeof(ini), "%s\\igi2hook.ini", g_dir);

    g_cfg.enableRedirect = GetPrivateProfileIntA("igi2hook", "enable_redirect", 0, ini);
    GetPrivateProfileStringA("igi2hook", "master_host", "", g_cfg.masterHost,(DWORD)sizeof(g_cfg.masterHost), ini);
    g_cfg.logBytes  = GetPrivateProfileIntA("igi2hook", "log_bytes", 96, ini);
    g_cfg.udpLogMax = GetPrivateProfileIntA("igi2hook", "log_udp_max", 400, ini);
    g_cfg.tcpLogMax = GetPrivateProfileIntA("igi2hook", "log_tcp_max", 200, ini);
    g_cfg.forceEnctype0 = GetPrivateProfileIntA("igi2hook", "force_enctype0", 0, ini);
    g_cfg.allowMulti = GetPrivateProfileIntA("igi2hook", "allow_multi", 0, ini);
    g_cfg.heartbeat = GetPrivateProfileIntA("igi2hook", "heartbeat", 0, ini);
    g_cfg.hostPort = GetPrivateProfileIntA("igi2hook", "host_port", 0, ini);
    g_cfg.masterUdpPort = GetPrivateProfileIntA("igi2hook", "master_udp_port", 27900, ini);
    g_cfg.heartbeatInterval = GetPrivateProfileIntA("igi2hook", "heartbeat_interval", 30, ini);
    if (g_cfg.heartbeatInterval < 5) g_cfg.heartbeatInterval = 5;
    GetPrivateProfileStringA("igi2hook", "gamename", "projectigi2r", g_cfg.gamename,(DWORD)sizeof(g_cfg.gamename), ini);
    if (g_cfg.logBytes < 0)   g_cfg.logBytes = 0;
    if (g_cfg.logBytes > 256) g_cfg.logBytes = 256;

    char pats[512];
    GetPrivateProfileStringA("igi2hook", "redirect_patterns", "gamespy.com,udpsoft.com",pats, (DWORD)sizeof(pats), ini);
    g_patCount = 0;
    char cur[64];
    size_t cl = 0;
    for (size_t i = 0;; ++i){
        char c = pats[i];
        if (c == ',' || c == ';' || c == ' ' || c == 0){
            if (cl > 0 && g_patCount < 16){
                cur[cl] = 0;
                snprintf(g_pats[g_patCount++], sizeof(g_pats[0]), "%s", cur);
            }
            cl = 0;
            if (c == 0) break;
        } else if (cl < sizeof(cur) - 1){
            cur[cl++] = (char)tolower((unsigned char)c);
        }
    }
}

static void OpenLog(){
    char path[MAX_PATH + 32];
    snprintf(path, sizeof(path), "%s\\igi2hook.log", g_dir);
    g_log = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL,CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
}

BOOL APIENTRY DllMain(HINSTANCE hInst, DWORD reason, LPVOID){
    if (reason == DLL_PROCESS_ATTACH){
        DisableThreadLibraryCalls(hInst);
        InitializeCriticalSection(&g_lock);
        LoadRealVersionDll();
        LoadConfig(hInst);
        OpenLog();

        char exePath[MAX_PATH] = "";
        GetModuleFileNameA(NULL, exePath, MAX_PATH);
        Log("igi2hook loaded into %s", exePath);
        Log("config: enable_redirect=%d master_host=\"%s\" log_bytes=%d patterns=%d",g_cfg.enableRedirect, g_cfg.masterHost, g_cfg.logBytes, g_patCount);
        for (int i = 0; i < g_patCount; ++i)Log("  pattern: %s", g_pats[i]);

        HANDLE t = CreateThread(NULL, 0, RetryThread, NULL, 0, NULL);
        if (t) CloseHandle(t);
    }
    return TRUE;
}