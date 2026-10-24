// Created By MotherOfProgrammers(MOP)
// IGI: Rampage Launcher - native C++ (Win32 + GDI+). No web view, no Qt, no external DLLs.
// Idle = zero CPU: it only redraws while something is animating.
#include <windows.h>
#include <windowsx.h>
#include <gdiplus.h>
#include <commdlg.h>
#include <shellapi.h>
#include <mmsystem.h>
#include <vector>
#include <string>
#include <cmath>
#include <cstring>
using namespace Gdiplus;

// data
static const wchar_t* ITEMS[5] = {L"IGI RAMPAGE", L"MULTIPLAYER", L"CONFIGURATIONS", L"CREDITS", L"EXIT"};
static const wchar_t* DESC[5]  = {L"Start the single-player campaign.", L"Join the fight with other players online or on LAN.",
    L"Set game file locations and launcher options.", L"The people behind the game and this launcher.", L"Close the launcher."};
enum{
    P_NONE,
    P_CFG,P_CRED
};

struct Cfg {std::wstring igi, igiArgs, mp, mpArgs;
    bool sound = true;
    }cfg;

struct R{
    float x, y, w, h;
    bool in(int px, int py) const {return px >= x && px < x + w && py >= y && py < y + h;} 
};

static HWND hw, hEd[4];
static int W, H;
static float U;
static HDC dcBack, dcBg; static HCURSOR curArrow, curBusy;
static HBRUSH brEdit;
static int sel = 0, hotId = -1, panel = P_NONE, loadWhich = 0;
static bool loading = false, timerOn = false, editsShown = false;
static float anim[5] = {1, 0, 0, 0, 0}, panelA = 0, pa = 1;
static ULONGLONG lastT, loadT0;
static float loadP = 0;
static std::wstring msg, iniPath;
static Font *fTitle, *fMenu, *fHead, *fBody, *fLbl, *fBtn, *fBig, *fHuge;
static float btnPx;
static StringFormat* sf;
static std::vector<BYTE> wav[3];

// helpers
static float Cl(float v, float a, float b){
    return v < a ? a : v > b ? b : v;
}

static Color C(int r, int g, int b, int a = 255){
    return Color((BYTE)(a * pa), (BYTE)r, (BYTE)g, (BYTE)b);
}

static void Txt(Graphics& g, const wchar_t* t, Font* f, const Brush& b, float x, float y){
    g.DrawString(t, -1, f, PointF(x, y), sf, &b);
}

static float Wd(Graphics& g, const wchar_t* t, Font* f){
    RectF r;
    g.MeasureString(t, -1, f, PointF(0, 0), sf, &r);
    return r.Width;
}

static std::wstring Sp(const wchar_t* s){
    std::wstring r;
    for (; *s; s++){
        r += *s;
        if (s[1]){
            r += L'\u2009';
            r += L'\u200A';
        }
    }
    return r;
}

static std::wstring Trim(std::wstring s){
    while (!s.empty() && (s.back() == L' ' || s.back() == L'"')) s.pop_back();
    size_t i = 0;
    while (i < s.size() && (s[i] == L' ' || s[i] == L'"')) i++;
    return s.substr(i);
}

static FontFamily* Fam(const wchar_t* n){
    FontFamily* f = new FontFamily(n);
    if (f->GetLastStatus() != Ok){
        delete f; f = FontFamily::GenericSansSerif()->Clone();
    }
    return f;
}

// sound (synthesised, no files)
static void Tone(std::vector<short>& s, float f0, float f1, float dur, bool saw, float vol) {
    const int Rt = 22050;
    size_t n = (size_t)(dur * Rt);
    if (s.size() < n) s.resize(n, 0);
    double ph = 0;
    for (size_t i = 0; i < n; i++){
        float t = i/(float)n;
        ph += f0 * pow(f1 / f0, t)/Rt;
        double w = saw ? 2 * (ph - floor(ph + .5)) : (ph - floor(ph) < .5 ? 1 : -1);
        int v = s[i] + (int)(w * pow(.002, t) * vol * 32767);
        s[i] = (short)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
    }
}

static std::vector<BYTE> Wav(const std::vector<short>& s) {
    std::vector<BYTE> b(44 + s.size() * 2);
    DWORD sz = (DWORD)s.size() * 2, v;
    auto w32 = [&](int o, DWORD x){memcpy(&b[o], &x, 4);};
    auto w16 = [&](int o, WORD x){memcpy(&b[o], &x, 2);};
    memcpy(&b[0], "RIFF", 4);
    w32(4, 36 + sz);
    memcpy(&b[8], "WAVEfmt ", 8);
    w32(16, 16);
    w16(20, 1);
    w16(22, 1);
    w32(24, 22050);
    v = 44100;
    w32(28, v);
    w16(32, 2);
    w16(34, 16);
    memcpy(&b[36], "data", 4);
    w32(40, sz);
    memcpy(&b[44], s.data(), sz);
    return b;
}

static void InitSounds() {
    std::vector<short> a, b, c;
    Tone(a, 1400, 1400, .04f, false, .12f);
    Tone(b, 220, 70, .18f, true, .22f);
    Tone(b, 900, 900, .05f, false, .12f);
    Tone(c, 500, 300, .08f, false, .12f);
    wav[0] = Wav(a);
    wav[1] = Wav(b);
    wav[2] = Wav(c);
}

static void Snd(int i){
    if (cfg.sound) PlaySoundW((LPCWSTR)wav[i].data(), 0, SND_MEMORY | SND_ASYNC | SND_NODEFAULT);
}

enum {
    S_HOVER,
    S_SELECT,
    S_BACK
};

// config (launcher.ini next to the exe)
static std::wstring Rd(const wchar_t* k){
    wchar_t b[1024];
    GetPrivateProfileStringW(L"launcher", k, L"", b, 1024, iniPath.c_str());
    return b;
}

static void Wr(const wchar_t* k, const std::wstring& v){
    WritePrivateProfileStringW(L"launcher", k, v.c_str(), iniPath.c_str());
}

static void LoadCfg(){
    cfg.igi = Rd(L"igi");
    cfg.igiArgs = Rd(L"igiArgs");
    cfg.mp = Rd(L"mp");
    cfg.mpArgs = Rd(L"mpArgs");
    cfg.sound = Rd(L"sound") != L"0";
}

static void SaveCfg(){
    Wr(L"igi", cfg.igi);
    Wr(L"igiArgs", cfg.igiArgs);
    Wr(L"mp", cfg.mp);
    Wr(L"mpArgs", cfg.mpArgs);
    Wr(L"sound", cfg.sound ? L"1" : L"0");
}

// layout
static R PanelR(){
    float pw = 500 * U;
    return R{W - 0.07f * W - pw, 0.12f * H, pw, (panel == P_CFG ? 440 : 265)* U};
}

static R MenuR(int i){
    float ih = 0.077f * H;
    return R{0.07f * W, 0.36f * H + i * ih, 440 * U, ih};
}

static R BtnR(int id) {
    R p = PanelR();
    switch (id){
        case 10:
            return R{p.x + 28 * U, p.y + 360 * U, 110 * U, 40 * U};
        case 11:
            return panel == P_CFG ? R{p.x + 150 * U, p.y + 360 * U, 110 * U, 40 * U} : R{p.x + 28 * U, p.y + 205 * U, 110 * U, 40 * U};
        case 12:
            return R{p.x + 28 * U, p.y + 318 * U, 220 * U, 24 * U};
        case 13:
            return R{p.x + p.w - 108 * U, p.y + 70 * U, 80 * U, 16 * U};
        case 14:
            return R{p.x + p.w - 108 * U, p.y + 194 * U, 80 * U, 16 * U}; }
    return R{0, 0, 0, 0};
}

static int Hit(int x, int y){
    if (loading) return -1;
    if (panel == P_CFG && panelA > .9f){
        for (int id = 10; id <= 14; id++) if (BtnR(id).in(x, y)) return id;
    }
    else if (panel == P_CRED && panelA > .9f && BtnR(11).in(x, y)) return 11;
    for (int i = 0; i < 5; i++) if (MenuR(i).in(x, y)) return i;
    return -1;
}

static void PlaceEdits(){
    R p = PanelR();
    for (int i = 0; i < 4; i++) MoveWindow(hEd[i], (int)(p.x + 28 * U), (int)(p.y + (88 + i * 62) * U), (int)(p.w - 56 * U), (int)(28 * U), TRUE);
}

// drawing
static void BuildBg() {   // drawn ONCE; every frame just copies it
    Graphics g(dcBg);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    SolidBrush base(Color(255, 5, 5, 5));
    g.FillRectangle(&base, 0, 0, W, H);
    GraphicsPath ep;
    ep.AddEllipse(RectF(W * .08f, H * -.5f, W * 1.4f, H * 1.8f));
    PathGradientBrush pg(&ep);
    pg.SetCenterPoint(PointF(W * .78f, H * .4f));
    pg.SetCenterColor(Color(255, 74, 74, 74));
    Color sc(255, 5, 5, 5); int n = 1;
    pg.SetSurroundColors(&sc, &n);
    g.FillRectangle(&pg, 0, 0, W, H);
    Pen st(Color(9, 255, 255, 255), 1);
    for (float x = 0; x < W + H; x += 140 * U) g.DrawLine(&st, x, 0.f, x - .176f * H, (float)H);
    float bx = W * .56f, bw = W * .38f, by = H * .22f, bh = H * .78f;
    float pc[8][2] = {{30, 0}, {60, 0}, {66, 14}, {80, 22}, {100, 100}, {0, 100}, {12, 30}, {28, 18}};
    PointF pt[8];
    for (int i = 0; i < 8; i++) pt[i] = PointF(bx + bw * pc[i][0] / 100, by + bh * pc[i][1] / 100);
    LinearGradientBrush sil(RectF(bx, by, bw, bh), Color(0, 0, 0, 0), Color(190, 0, 0, 0), LinearGradientModeVertical);
    g.FillPolygon(&sil, pt, 8);
    LinearGradientBrush fade(RectF(0, H * .55f, (float)W, H * .46f), Color(0, 0, 0, 0), Color(255, 0, 0, 0), LinearGradientModeVertical);
    g.FillRectangle(&fade, 0.f, H * .55f, (float)W, H * .46f);
    GraphicsPath vp; vp.AddEllipse(RectF(-W * .2f, -H * .2f, W * 1.4f, H * 1.4f));
    PathGradientBrush vg(&vp);
    vg.SetCenterColor(Color(0, 0, 0, 0));
    Color ec(210, 0, 0, 0);
    vg.SetSurroundColors(&ec, &n);
    REAL f[3] = {0, 1, 1}, ps[3] = {0, .4f, 1};
    vg.SetBlend(f, ps, 3);
    g.FillRectangle(&vg, 0, 0, W, H);
}

static void DrawBtn(Graphics& g, R r, const wchar_t* t, bool hotStyle, bool hover) {
    SolidBrush b(hover ? C(255, 255, 255) : hotStyle ? C(200, 16, 46) : C(34, 34, 34)), f(hover ? C(0, 0, 0) : hotStyle ? C(255, 255, 255) : C(221, 221, 221));
    g.FillRectangle(&b, r.x, r.y, r.w, r.h);
    Txt(g, t, fBtn, f, r.x + (r.w - Wd(g, t, fBtn)) / 2, r.y + (r.h - btnPx * 1.22f) / 2);
}

static void DrawMain(Graphics& g) {
    pa = 1;
    SolidBrush wh(C(242, 242, 242)), red(C(200, 16, 46)), dim(C(109, 109, 109)), g2(C(187, 187, 187)), g3(C(85, 85, 85));
    float x0 = .07f * W, y0 = .07f * H, ts = .09f * H;
    Txt(g, L"IGI", fTitle, wh, x0, y0); Txt(g, L":", fTitle, red, x0 + Wd(g, L"IGI", fTitle), y0);
    Txt(g, L"RAMPAGE", fTitle, wh, x0, y0 + ts * .98f);
    Txt(g, Sp(L"A GENIGI MOD FOR PROJECT I.G.I.").c_str(), fLbl, dim, x0, y0 + ts * 2.1f);
    float fs = .046f * H;
    for (int i = 0; i < 5; i++) { R r = MenuR(i); float a = anim[i];
        if (a > .003f){
            LinearGradientBrush gb(RectF(r.x, r.y, r.w * a + 1, r.h), Color(255, 200, 16, 46), Color(0, 200, 16, 46), LinearGradientModeHorizontal);
            g.FillRectangle(&gb, r.x, r.y, r.w * a + 1, r.h);
            SolidBrush bar(Color((BYTE)(255 * a), 242, 242, 242));
            g.FillRectangle(&bar, r.x, r.y, 5 * U, r.h); }
        int c = (int)(109 + 146 * a); SolidBrush tb(Color(255, c, c, c));
        Txt(g, ITEMS[i], fMenu, tb, r.x + 22 * U, r.y + (r.h - fs * 1.22f) / 2);
    }
    g.FillRectangle(&red, x0, H * .87f, 3 * U, 22 * U); Txt(g, DESC[sel], fBody, g2, x0 + 17 * U, H * .87f + 1 * U);
    std::wstring v = Sp(L"LAUNCHER V1.2");
    Txt(g, v.c_str(), fLbl, g3, W * .97f - Wd(g, v.c_str(), fLbl), H * .96f - 12 * U);
}

static void DrawPanel(Graphics& g){
    pa = panelA; g.TranslateTransform((1 - pa) * 24 * U, 0); R p = PanelR(); float x = p.x + 28 * U;
    SolidBrush bg(C(0, 0, 0, 224)), red(C(200, 16, 46)), wh(C(255, 255, 255)), gr(C(109, 109, 109)), lt(C(204, 204, 204));
    g.FillRectangle(&bg, p.x, p.y, p.w, p.h);
    g.FillRectangle(&red, p.x, p.y, p.w, 4 * U);
    if (panel == P_CFG){
        Txt(g, L"CONFIGURATIONS", fHead, wh, x, p.y + 20 * U);
        const wchar_t* L4[4] = {L"IGI RAMPAGE EXECUTABLE (full path)", L"LAUNCH ARGUMENTS (optional)", L"MULTIPLAYER EXECUTABLE (full path)", L"MULTIPLAYER ARGUMENTS (optional)"};
        for (int i = 0; i < 4; i++) Txt(g, L4[i], fLbl, gr, x, p.y + (70 + i * 62) * U);
        for (int id = 13; id <= 14; id++){
            R b = BtnR(id);
            Txt(g, L"BROWSE", fLbl, hotId == id ? red : lt, b.x, b.y);
        }
        R s = BtnR(12);
        float bs = 14 * U;
        Pen pn(C(120, 120, 120), 1.5f);
        g.DrawRectangle(&pn, s.x, s.y + 3 * U, bs, bs);
        if (cfg.sound) g.FillRectangle(&red, s.x + 3 * U, s.y + 6 * U, bs - 5.5f * U, bs - 5.5f * U);
        Txt(g, L"Menu sounds", fBody, hotId == 12 ? wh : lt, s.x + 26 * U, s.y);
        DrawBtn(g, BtnR(10), L"SAVE", true, hotId == 10);
        DrawBtn(g, BtnR(11), L"BACK", false, hotId == 11);
        Txt(g, msg.c_str(), fBody, red, x, p.y + 410 * U);
    } else{
        Txt(g, L"CREDITS", fHead, wh, x, p.y + 20 * U); Txt(g, L"Mod developed by", fBody, lt, x, p.y + 78 * U);
        Txt(g, L"GEN", fBig, wh, x, p.y + 98 * U); Txt(g, L"IGI", fBig, red, x + Wd(g, L"GEN", fBig), p.y + 98 * U);
        Txt(g, L"Original games by Innerloop Studios.", fBody, lt, x, p.y + 158 * U);
        Txt(g, L"Launcher built in C++ with Win32 and GDI+.", fBody, lt, x, p.y + 180 * U);
        DrawBtn(g, BtnR(11), L"BACK", true, hotId == 11);
    }
}

static void DrawLoad(Graphics& g){
    pa = 1;
    SolidBrush bk(Color(255, 0, 0, 0)), wh(Color(255, 242, 242, 242)), bgb(Color(255, 34, 34, 34)), red(Color(255, 200, 16, 46)), dim(Color(255, 109, 109, 109));
    g.FillRectangle(&bk, 0, 0, W, H);
    float x = .07f * W, w = W * .86f;
    Txt(g, loadWhich == 0 ? L"IGI RAMPAGE" : L"MULTIPLAYER", fHuge, wh, x, H * .76f);
    g.FillRectangle(&bgb, x, H * .87f, w, 4 * U);
    g.FillRectangle(&red, x, H * .87f, w * loadP, 4 * U);
    Txt(g, Sp(L"LOADING").c_str(), fLbl, dim, x, H * .87f + 12 * U);
}

static void Render(HDC dst){
    BitBlt(dcBack, 0, 0, W, H, dcBg, 0, 0, SRCCOPY);
    {Graphics g(dcBack);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    g.SetTextRenderingHint(TextRenderingHintAntiAlias);
      if (loading) DrawLoad(g); else { DrawMain(g); if (panel && panelA > .01f) DrawPanel(g); }}
    BitBlt(dst, 0, 0, W, H, dcBack, 0, 0, SRCCOPY);
}

// actions
static void Kick(){
    if (!timerOn){
        timerOn = true;
        lastT = GetTickCount64();
        SetTimer(hw, 1, 10, 0);
    }
}

static void SetPanel(int p){
    panel = p; panelA = 0;
    msg.clear();
    SetFocus(hw);
    if (p == P_CFG){
        SetWindowTextW(hEd[0], cfg.igi.c_str());
        SetWindowTextW(hEd[1], cfg.igiArgs.c_str());
        SetWindowTextW(hEd[2], cfg.mp.c_str());
        SetWindowTextW(hEd[3], cfg.mpArgs.c_str());
    }
    Kick();
}

static void ClosePanel(){
    if (panel){
        Snd(S_BACK);
        panel = P_NONE;
        panelA = 0; Kick();
    }
}

static std::wstring GetEd(int i){
    wchar_t b[1024];
    GetWindowTextW(hEd[i], b, 1024);
    return Trim(b);
}

static void Browse(int edit){
    wchar_t f[1024] = L"";
    OPENFILENAMEW o = {sizeof o};
    o.hwndOwner = hw;
    o.lpstrFilter = L"Executable (*.exe)\0*.exe\0All files\0*.*\0";
    o.lpstrFile = f;
    o.nMaxFile = 1024;
    o.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (GetOpenFileNameW(&o)) SetWindowTextW(hEd[edit], f);
}

static void StartLaunch(int which){
    const std::wstring& path = which == 0 ? cfg.igi : cfg.mp;
    if (path.empty()){
        SetPanel(P_CFG);
        msg = std::wstring(L"Set the ") + (which == 0 ? L"IGI Rampage" : L"Multiplayer") + L" executable first, then save.";
        return;
    }
    loading = true;
    loadWhich = which;
    loadP = 0;
    loadT0 = GetTickCount64();
    panel = P_NONE;
    SetCursor(curBusy);
    Kick();
}

static void FinishLoad(){
    const std::wstring& path = loadWhich == 0 ? cfg.igi : cfg.mp; const std::wstring& args = loadWhich == 0 ? cfg.igiArgs : cfg.mpArgs;
    DWORD at = GetFileAttributesW(path.c_str());
    std::wstring err;
    if (at == INVALID_FILE_ATTRIBUTES || (at & FILE_ATTRIBUTE_DIRECTORY)) err = L"File not found: " + path;
    else {
        std::wstring dir = path.substr(0, path.find_last_of(L"\\/"));
        if ((INT_PTR)ShellExecuteW(hw, L"open", path.c_str(), args.empty() ? 0 : args.c_str(), dir.c_str(), SW_SHOWNORMAL) > 32) {
            PostQuitMessage(0);
            return;
        }
        err = L"Windows could not start the game.";
       }
    loading = false; SetCursor(curArrow); SetPanel(P_CFG); msg = err;
}

static void Activate(int i){
    switch (i){case 0: case 1: StartLaunch(i); break; case 2: SetPanel(P_CFG); break; case 3: SetPanel(P_CRED); break; case 4: DestroyWindow(hw); break;}
}

static void Tick() {
    ULONGLONG n = GetTickCount64();
    float dt = Cl((n - lastT)/1000.f, 0, .05f);
    lastT = n;
    bool act = false;
    for (int i = 0; i < 5; i++){
        float t = (i == sel && !loading) ? 1.f : 0.f, d = t - anim[i];
        if (fabsf(d) > .004f){
            anim[i] += d * Cl(dt * 20, 0, 1);
            act = true;
        } else anim[i] = t;
    }

    float pt = panel ? 1.f : 0.f, d = pt - panelA;
    if (fabsf(d) > .004f){
        panelA += d * Cl(dt * 14, 0, 1);
        act = true;
    } else panelA = pt;
    if (loading){
        float p = Cl((n - loadT0)/1800.f, 0, 1);
        loadP = 1 - (1 - p) * (1 - p);
        act = true;
        if (p >= 1){
            FinishLoad();
            act = true;
        }
    }

    bool want = panel == P_CFG && panelA > .98f && !loading;
    if (want != editsShown){
        editsShown = want;
    for (int i = 0; i < 4; i++) ShowWindow(hEd[i], want ? SW_SHOWNA : SW_HIDE);
    }

    HDC d2 = GetDC(hw); Render(d2);
    ReleaseDC(hw, d2);
    if (!act){
        KillTimer(hw, 1);
        timerOn = false;
    }
}

// window procedure
static LRESULT CALLBACK Proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    switch (m){
    case WM_TIMER:
        Tick();
        return 0;
    case WM_PAINT:
        {PAINTSTRUCT ps; HDC d = BeginPaint(h, &ps); Render(d); EndPaint(h, &ps); return 0;}
    case WM_ERASEBKGND:
        return 1;
    case WM_SETCURSOR:
        if (LOWORD(l) == HTCLIENT){
            SetCursor(loading ? curBusy : curArrow);
            return TRUE;
        }
        break;
    case WM_CTLCOLOREDIT:
        SetTextColor((HDC)w, RGB(255, 255, 255));
        SetBkColor((HDC)w, RGB(17, 17, 17));
        return (LRESULT)brEdit;
    case WM_MOUSEMOVE:{
        int id = Hit(GET_X_LPARAM(l), GET_Y_LPARAM(l));
        if (id != hotId){
            hotId = id;
            if (id >= 0 && id < 5 && id != sel){
                sel = id;
                Snd(S_HOVER);
            }
            Kick();
        }
        return 0;
    }
    case WM_LBUTTONDOWN:{
        SetFocus(h);
        int id = Hit(GET_X_LPARAM(l), GET_Y_LPARAM(l));
        if (id >= 0 && id < 5){
            Snd(S_SELECT);
            Activate(id);
        }
        else if (id == 10){
            cfg.igi = GetEd(0);
            cfg.igiArgs = GetEd(1);
            cfg.mp = GetEd(2);
            cfg.mpArgs = GetEd(3);
            SaveCfg();
            msg = L"Saved.";
            Snd(S_SELECT);
            Kick();
        }
        else if (id == 11) ClosePanel();
        else if (id == 12) {
            cfg.sound = !cfg.sound;
            Snd(S_SELECT);
            Kick();
        }
        else if (id == 13) Browse(0); else if (id == 14) Browse(2);
        return 0;
    }
    case WM_KEYDOWN: if (loading) return 0;
        if (w == VK_DOWN || w == VK_UP){
            sel = (sel + (w == VK_DOWN ? 1 : 4)) % 5;
            Snd(S_HOVER);
            Kick();
        }
        else if (w == VK_RETURN){
            Snd(S_SELECT);
            Activate(sel);
        } else if (w == VK_ESCAPE) ClosePanel();
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(h, m, w, l);
}

// cursors (drawn in code)
static HCURSOR MakeCur(bool busy){
    Bitmap b(32, 32, PixelFormat32bppARGB);
    Graphics g(&b);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    Pen blk(Color(255, 0, 0, 0), 1.6f), rd(Color(255, 200, 16, 46), 3.f), wp(Color(255, 255, 255, 255), 2.f);
    SolidBrush wh(Color(255, 255, 255, 255));
    if (!busy){
        PointF p[7] = {PointF(3, 2), PointF(3, 22), PointF(8.5f, 16.8f), PointF(12.3f, 25), PointF(15.7f, 23.4f), PointF(11.9f, 15.4f), PointF(20, 15.4f)};
        g.FillPolygon(&wh, p, 7); g.DrawPolygon(&blk, p, 7); g.DrawLine(&rd, 3.f, 2.f, 3.f, 8.f);
    }
    else{
        g.DrawEllipse(&wp, 7.f, 7.f, 18.f, 18.f);
        g.DrawLine(&rd, 16.f, 2.f, 16.f, 10.f);
        g.DrawLine(&rd, 16.f, 22.f, 16.f, 30.f);
        g.DrawLine(&rd, 2.f, 16.f, 10.f, 16.f);
        g.DrawLine(&rd, 22.f, 16.f, 30.f, 16.f);
        g.FillEllipse(&wh, 14.f, 14.f, 4.f, 4.f);
    }
    HICON ic;
    b.GetHICON(&ic);
    ICONINFO ii;
    GetIconInfo(ic, &ii);
    ii.fIcon = FALSE;
    ii.xHotspot = busy ? 16 : 3;
    ii.yHotspot = busy ? 16 : 2;
    HCURSOR c = (HCURSOR)CreateIconIndirect(&ii);
    DeleteObject(ii.hbmColor);
    DeleteObject(ii.hbmMask);
    DestroyIcon(ic);
    return c;
}

// entry
int WINAPI WinMain(HINSTANCE inst, HINSTANCE, LPSTR, int){
    SetProcessDPIAware();
    GdiplusStartupInput gi;
    ULONG_PTR tok;
    GdiplusStartup(&tok, &gi, 0);
    W = GetSystemMetrics(SM_CXSCREEN);
    H = GetSystemMetrics(SM_CYSCREEN);
    U = H/768.f;
    wchar_t ex[MAX_PATH]; GetModuleFileNameW(0, ex, MAX_PATH);
    iniPath = ex;
    iniPath = iniPath.substr(0, iniPath.find_last_of(L'\\')) + L"\\launcher.ini"; LoadCfg();
    WNDCLASSW wc = {};
    wc.lpfnWndProc = Proc;
    wc.hInstance = inst;
    wc.lpszClassName = L"IGIRampageLauncher";
    RegisterClassW(&wc);
    hw = CreateWindowExW(WS_EX_APPWINDOW, wc.lpszClassName, L"IGI: Rampage", WS_POPUP | WS_CLIPCHILDREN, 0, 0, W, H, 0, 0, inst, 0);
    HDC scr = GetDC(0);
    dcBack = CreateCompatibleDC(scr);
    dcBg = CreateCompatibleDC(scr);
    SelectObject(dcBack, CreateCompatibleBitmap(scr, W, H));
    SelectObject(dcBg, CreateCompatibleBitmap(scr, W, H));
    ReleaseDC(0, scr);
    sf = StringFormat::GenericTypographic()->Clone();
    sf->SetFormatFlags(StringFormatFlagsNoWrap | StringFormatFlagsMeasureTrailingSpaces);
    FontFamily* imp = Fam(L"Impact");
    FontFamily* seg = Fam(L"Segoe UI");
    fTitle = new Font(imp, .09f * H, FontStyleRegular, UnitPixel);

    fMenu = new Font(imp, .046f * H, FontStyleRegular, UnitPixel);
    fHead = new Font(imp, 32 * U, FontStyleRegular, UnitPixel);
    fBtn = new Font(imp, 20 * U, FontStyleRegular, UnitPixel);
    btnPx = 20 * U;

    fBig = new Font(imp, 46 * U, FontStyleRegular, UnitPixel);
    fHuge = new Font(imp, .065f * H, FontStyleRegular, UnitPixel);
    fBody = new Font(seg, 15 * U, FontStyleRegular, UnitPixel);
    fLbl = new Font(seg, 12 * U, FontStyleRegular, UnitPixel);

    BuildBg();
    InitSounds();
    curArrow = MakeCur(false);
    curBusy = MakeCur(true);
    brEdit = CreateSolidBrush(RGB(17, 17, 17));
    HFONT ef = CreateFontW(-(int)(15 * U), 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");

    for (int i = 0; i < 4; i++){
        hEd[i] = CreateWindowExW(0, L"EDIT", L"", WS_CHILD | WS_BORDER | ES_AUTOHSCROLL, 0, 0, 10, 10, hw, (HMENU)(INT_PTR)(101 + i), inst, 0);
        SendMessageW(hEd[i], WM_SETFONT, (WPARAM)ef, TRUE);
    }

    PlaceEdits();
    ShowWindow(hw, SW_SHOW);
    SetForegroundWindow(hw);
    SetFocus(hw);
    MSG msgs;

    while (GetMessageW(&msgs, 0, 0, 0) > 0){
        TranslateMessage(&msgs);
        DispatchMessageW(&msgs);
    }
    return 0;
}
