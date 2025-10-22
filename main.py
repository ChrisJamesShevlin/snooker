#!/usr/bin/env python3
import math
import tkinter as tk
from tkinter import ttk

# ---------- math helpers ----------
def clip(x, lo, hi): 
    return max(lo, min(hi, x))

def logit(p):
    p = clip(p, 1e-6, 1-1e-6)
    return math.log(p/(1-p))

def inv_logit(z): 
    return 1/(1+math.exp(-z))

# DP race model: P(match | per-frame p, score a-b, target)
def match_win_prob(p, a, b, target, memo=None):
    if memo is None: memo = {}
    key = (a, b)
    if a >= target: return 1.0
    if b >= target: return 0.0
    if key in memo: return memo[key]
    memo[key] = p*match_win_prob(p, a+1, b, target, memo) + (1-p)*match_win_prob(p, a, b+1, target, memo)
    return memo[key]

# ---------- modelling ----------
def season_strength(points_scored, matches_played, win_rate, avg_shot_time, b50, b100,
                    w_wr, w_ppm, w_b50, w_b100, w_shot, scale):
    mp = max(1, int(round(matches_played)))
    ppm  = points_scored / mp
    r50  = b50  / mp
    r100 = b100 / mp
    # Soft league-average centres
    ppm_c, r50_c, r100_c, shot_c = 300.0, 1.0, 0.15, 30.0
    idx = (
        w_wr   * ((win_rate/100.0) - 0.50) +
        w_ppm  * ((ppm  - ppm_c)/ppm_c) +
        w_b50  * ((r50  - r50_c)/max(0.3, r50_c)) +
        w_b100 * ((r100 - r100_c)/max(0.05, r100_c)) +
        w_shot * ((shot_c - avg_shot_time)/shot_c)  # faster than ~30s = positive
    )
    return scale * idx

def live_boost(potA, potB, stA, stB, b50A, b50B, b100A, b100B, hbA, hbB,
               ptsA, ptsB, shotsA, shotsB, totA, totB,
               w_pot, w_st, w_b50, w_b100, w_hb, w_pts, w_shots, w_tot,
               sd_pot, sd_st, sd_b50, sd_b100, sd_hb, sd_pts_share, sd_shots_share, sd_tot_share,
               k_shots, beta):
    def z(diff, sd): 
        return clip(diff/max(sd,1e-9), -3.0, 3.0)

    shots_tot = max(1, shotsA + shotsB)
    w_rel = clip(shots_tot / max(1, k_shots), 0.0, 1.0)

    pot_diff   = (potA - potB) / 100.0
    st_diff    = (stB - stA)                 # faster A => positive
    b50_diff   = b50A - b50B
    b100_diff  = b100A - b100B
    hb_diff    = (hbA - hbB) / 100.0
    pts_share  = ptsA / max(1e-9, (ptsA+ptsB))
    shots_share= shotsA/ max(1e-9, (shotsA+shotsB))
    tot_share  = (totA/100.0)

    S = (
        w_pot   * z(pot_diff, sd_pot/100.0) +
        w_st    * z(st_diff,  sd_st) +
        w_b50   * z(b50_diff, sd_b50) +
        w_b100  * z(b100_diff,sd_b100) +
        w_hb    * z(hb_diff,  sd_hb/100.0) +
        w_pts   * z(pts_share-0.5,  sd_pts_share) +
        w_shots * z(shots_share-0.5,sd_shots_share) +
        w_tot   * z((tot_share-0.5),sd_tot_share)
    )
    return beta * w_rel * S  # add directly to logit space

# ---------- scrollable app ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Snooker In-Play — Match Odds (Season + Live + Score) [Realism]")
        self.geometry("1100x800")
        self.configure(bg="#0e0f13")
        self._style()

        # Scroll container
        canvas = tk.Canvas(self, bg="#0e0f13", highlightthickness=0)
        vbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.root = ttk.Frame(canvas, padding=14)
        self.root.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.root, anchor="nw")

        # Mouse wheel
        def _on_mousewheel(event):
            delta = -1*(event.delta//120) if event.delta else (1 if event.num==5 else -1)
            canvas.yview_scroll(delta, "units")
        self.bind_all("<MouseWheel>", _on_mousewheel)      # Windows/macOS
        self.bind_all("<Button-4>", _on_mousewheel)        # Linux up
        self.bind_all("<Button-5>", _on_mousewheel)        # Linux down

        # Columns
        self.colL = ttk.Labelframe(self.root, text="Season (pre-match) — from 'Season' screenshot", padding=10)
        self.colM = ttk.Labelframe(self.root, text="In-Play — from 'Match' screenshot", padding=10)
        self.colR = ttk.Labelframe(self.root, text="Outputs, Score & Book odds", padding=10)
        self.colL.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        self.colM.grid(row=0, column=1, sticky="nsew", padx=8)
        self.colR.grid(row=0, column=2, sticky="nsew", padx=(8,0))
        self.root.columnconfigure((0,1,2), weight=1)

        self._season_inputs()
        self._live_inputs()
        self._outputs()

        ttk.Button(self.colR, text="Update", command=self.update_all).pack(fill="x", pady=10)

    # ---- style
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        BG = "#0e0f13"; PANEL="#141720"; FG="#e6ebff"; ACC="#37a3ff"
        s.configure(".", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure("TLabelframe", background=PANEL, foreground=ACC, borderwidth=1)
        s.configure("TLabelframe.Label", background=PANEL, foreground=ACC)
        s.configure("TEntry", fieldbackground="#0f121a", foreground=FG)
        s.configure("TButton", background=ACC, foreground="#06111a")
        s.map("TButton", background=[("active","#4fb1ff")])
        s.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=ACC)

    # ---- small UI helpers
    def _ef(self, parent, text, val="", w=9):
        row = ttk.Frame(parent); row.pack(fill="x", pady=2)
        ttk.Label(row, text=text).pack(side="left")
        var = tk.StringVar(value=str(val))
        ttk.Entry(row, textvariable=var, width=w).pack(side="right")
        return var

    def _slider(self, parent, label, val, to=2.0, res=0.1):
        row = ttk.Frame(parent); row.pack(fill="x", pady=2)
        ttk.Label(row, text=label).pack(side="left")
        var = tk.DoubleVar(value=val)
        ttk.Scale(row, variable=var, from_=0.0, to=to, orient="horizontal").pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Label(row, textvariable=var).pack(side="right")
        return var

    def _kv(self, parent, k, v):
        r = ttk.Frame(parent); r.pack(fill="x", pady=2)
        ttk.Label(r, text=k).pack(side="left")
        ttk.Label(r, textvariable=v, foreground="#37a3ff").pack(side="right")

    def _f(self, var, d=None, required=False, to_int=False):
        s = var.get().strip()
        if s == "":
            if required:
                raise ValueError("missing")
            return d
        return int(float(s)) if to_int else float(s)

    # -------- season inputs --------
    def _season_inputs(self):
        ttk.Label(self.colL, text="Player A — Season", style="Header.TLabel").pack(anchor="w", pady=(0,4))
        self.A_points = self._ef(self.colL, "Points scored:")
        self.A_mp     = self._ef(self.colL, "Matches played:")
        self.A_wr     = self._ef(self.colL, "Match win rate %:")
        self.A_st     = self._ef(self.colL, "Avg shot time (s):")
        self.A_b50    = self._ef(self.colL, "50+ breaks:")
        self.A_b100   = self._ef(self.colL, "100+ breaks:")

        ttk.Separator(self.colL).pack(fill="x", pady=6)
        ttk.Label(self.colL, text="Player B — Season", style="Header.TLabel").pack(anchor="w", pady=(6,4))
        self.B_points = self._ef(self.colL, "Points scored:")
        self.B_mp     = self._ef(self.colL, "Matches played:")
        self.B_wr     = self._ef(self.colL, "Match win rate %:")
        self.B_st     = self._ef(self.colL, "Avg shot time (s):")
        self.B_b50    = self._ef(self.colL, "50+ breaks:")
        self.B_b100   = self._ef(self.colL, "100+ breaks:")

        ttk.Separator(self.colL).pack(fill="x", pady=8)
        ttk.Label(self.colL, text="Season Weights", style="Header.TLabel").pack(anchor="w", pady=(6,4))
        # UPDATED DEFAULTS
        self.w_wr   = self._slider(self.colL, "Weight: Win rate", 0.82)        # was 0.80
        self.w_ppm  = self._slider(self.colL, "Weight: Points per match", 0.70) # was 0.80
        self.w_b50  = self._slider(self.colL, "Weight: 50+ per match", 0.60)    # was 0.70
        self.w_b100 = self._slider(self.colL, "Weight: 100+ per match", 0.40)   # was 0.60
        self.w_shot = self._slider(self.colL, "Weight: Shot time (faster=better)", 0.46)  # was 0.60
        self.season_scale = self._slider(self.colL, "Season strength scale", 0.72, to=2.0) # was 0.80

    # -------- live inputs --------
    def _live_inputs(self):
        ttk.Label(self.colM, text="Player A — Live (Match tab)", style="Header.TLabel").pack(anchor="w", pady=(0,4))
        self.A_pot   = self._ef(self.colM, "Pot rate %:")
        self.A_stL   = self._ef(self.colM, "Avg shot time (s):")
        self.A_b50L  = self._ef(self.colM, "50+ breaks:")
        self.A_b100L = self._ef(self.colM, "100+ breaks:")
        self.A_hb    = self._ef(self.colM, "Highest break:")
        self.A_pts   = self._ef(self.colM, "Total match points:")
        self.A_shots = self._ef(self.colM, "Shots taken:")
        self.A_tot   = self._ef(self.colM, "Time on table %:")

        ttk.Separator(self.colM).pack(fill="x", pady=6)
        ttk.Label(self.colM, text="Player B — Live (Match tab)", style="Header.TLabel").pack(anchor="w", pady=(6,4))
        self.B_pot   = self._ef(self.colM, "Pot rate %:")
        self.B_stL   = self._ef(self.colM, "Avg shot time (s):")
        self.B_b50L  = self._ef(self.colM, "50+ breaks:")
        self.B_b100L = self._ef(self.colM, "100+ breaks:")
        self.B_hb    = self._ef(self.colM, "Highest break:")
        self.B_pts   = self._ef(self.colM, "Total match points:")
        self.B_shots = self._ef(self.colM, "Shots taken:")
        self.B_tot   = self._ef(self.colM, "Time on table %:")

        ttk.Separator(self.colM).pack(fill="x", pady=8)
        ttk.Label(self.colM, text="Live Weights / SDs / Reliability", style="Header.TLabel").pack(anchor="w", pady=(6,4))
        # UPDATED DEFAULTS
        self.w_pot   = self._slider(self.colM, "Weight: Pot %", 0.52)       # was 1.00
        self.w_st    = self._slider(self.colM, "Weight: Shot time", 0.44)   # was 0.70
        self.w_b50   = self._slider(self.colM, "Weight: 50+ count", 0.34)   # was 0.60
        self.w_b100  = self._slider(self.colM, "Weight: 100+ count", 0.12)  # was 0.50
        self.w_hb    = self._slider(self.colM, "Weight: Highest break", 0.20) # was 0.40
        self.w_pts   = self._slider(self.colM, "Weight: Points share", 0.68)  # was 1.20
        self.w_shots = self._slider(self.colM, "Weight: Shots share", 0.43)    # was 0.60
        self.w_tot   = self._slider(self.colM, "Weight: Time-on-table share", 0.44) # was 0.60

        # SDs (more conservative defaults)
        self.sd_pot  = self._slider(self.colM, "SD: Pot % (pp)", 8.0, to=15.0)
        self.sd_st   = self._slider(self.colM, "SD: Shot time (s)", 2.2, to=6.0)
        self.sd_b50  = self._slider(self.colM, "SD: 50+ diff (count)", 1.8, to=5.0)
        self.sd_b100 = self._slider(self.colM, "SD: 100+ diff (count)", 1.0, to=3.0)
        self.sd_hb   = self._slider(self.colM, "SD: Highest break (pp of 100)", 30.0, to=50.0)
        self.sd_ptsS = self._slider(self.colM, "SD: Points share", 0.18, to=0.30)
        self.sd_shS  = self._slider(self.colM, "SD: Shots share", 0.18, to=0.30)
        self.sd_totS = self._slider(self.colM, "SD: ToT share", 0.16, to=0.30)

        # Reliability & live effect
        self.k_shots = self._slider(self.colM, "Reliability k (total shots)", 150, to=300, res=1)
        self.beta    = self._slider(self.colM, "β scale (live effect)", 0.25, to=1.0, res=0.01)

        ttk.Separator(self.colM).pack(fill="x", pady=8)
        ttk.Label(self.colM, text="Realism guards", style="Header.TLabel").pack(anchor="w", pady=(6,4))
        self.lambda_shrink = self._slider(self.colM, "Realism shrink λ (0–1)", 0.70, to=1.0, res=0.01)
        # cap toggle + min/max
        row = ttk.Frame(self.colM); row.pack(fill="x", pady=2)
        self.cap_on = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, variable=self.cap_on, text="Cap per-frame p to [min, max]").pack(side="left")
        # UPDATED DEFAULTS
        self.pmin = tk.DoubleVar(value=0.45)  # was 0.20
        self.pmax = tk.DoubleVar(value=0.66)  # was 0.80
        ttk.Entry(row, textvariable=self.pmin, width=5).pack(side="right")
        ttk.Label(row, text="max").pack(side="right", padx=4)
        ttk.Entry(row, textvariable=self.pmax, width=5).pack(side="right")
        ttk.Label(row, text="min").pack(side="right", padx=4)

    # -------- outputs & score --------
    def _outputs(self):
        ttk.Label(self.colR, text="Match state (score)", style="Header.TLabel").pack(anchor="w", pady=(0,6))
        self.bestof = self._ef(self.colR, "Best-of (e.g., 7, 11, 19):")
        self.a_won  = self._ef(self.colR, "Frames won — Player A:")
        self.b_won  = self._ef(self.colR, "Frames won — Player B:")

        ttk.Separator(self.colR).pack(fill="x", pady=8)
        ttk.Label(self.colR, text="Fair Prices", style="Header.TLabel").pack(anchor="w", pady=(0,6))
        self.out_p_frame = tk.StringVar(value="")
        self.out_o_frame = tk.StringVar(value="")
        self.out_p_match = tk.StringVar(value="")
        self.out_oA      = tk.StringVar(value="")
        self.out_oB      = tk.StringVar(value="")
        self._kv(self.colR, "Per-frame win p (A):", self.out_p_frame)
        self._kv(self.colR, "Per-frame fair odds:", self.out_o_frame)
        self._kv(self.colR, "Match win p (A) — score-adjusted:", self.out_p_match)
        self._kv(self.colR, "Player A fair odds (match):", self.out_oA)
        self._kv(self.colR, "Player B fair odds (match):", self.out_oB)

        ttk.Separator(self.colR).pack(fill="x", pady=8)
        ttk.Label(self.colR, text="Book Back Odds (match)", style="Header.TLabel").pack(anchor="w", pady=(0,6))
        self.bookA = self._ef(self.colR, "Book back odds A:")
        self.bookB = self._ef(self.colR, "Book back odds B:")
        ttk.Button(self.colR, text="Compare Value", command=self.compare_value).pack(fill="x", pady=6)
        self.value_txt = tk.StringVar(value="")
        ttk.Label(self.colR, textvariable=self.value_txt, foreground="#37a3ff", justify="left").pack(anchor="w")

        ttk.Separator(self.colR).pack(fill="x", pady=8)
        self.hint = tk.StringVar(value="Fill season + live + score, then click Update.")
        ttk.Label(self.colR, textvariable=self.hint, justify="left").pack(anchor="w")

    # ---- actions
    def update_all(self):
        try:
            # Season strengths (require main fields)
            SA = season_strength(
                points_scored=self._f(self.A_points, required=True),
                matches_played=self._f(self.A_mp, required=True),
                win_rate=self._f(self.A_wr, required=True),
                avg_shot_time=self._f(self.A_st, required=True),
                b50=self._f(self.A_b50, 0.0), 
                b100=self._f(self.A_b100, 0.0),
                w_wr=self.w_wr.get(), w_ppm=self.w_ppm.get(), w_b50=self.w_b50.get(),
                w_b100=self.w_b100.get(), w_shot=self.w_shot.get(), scale=self.season_scale.get()
            )
            SB = season_strength(
                points_scored=self._f(self.B_points, required=True),
                matches_played=self._f(self.B_mp, required=True),
                win_rate=self._f(self.B_wr, required=True),
                avg_shot_time=self._f(self.B_st, required=True),
                b50=self._f(self.B_b50, 0.0), 
                b100=self._f(self.B_b100, 0.0),
                w_wr=self.w_wr.get(), w_ppm=self.w_ppm.get(), w_b50=self.w_b50.get(),
                w_b100=self.w_b100.get(), w_shot=self.w_shot.get(), scale=self.season_scale.get()
            )
            base_logit = (SA - SB)

            # Live boost (require core live fields)
            boost = live_boost(
                potA=self._f(self.A_pot, required=True), potB=self._f(self.B_pot, required=True),
                stA=self._f(self.A_stL, required=True),  stB=self._f(self.B_stL, required=True),
                b50A=self._f(self.A_b50L, 0.0), b50B=self._f(self.B_b50L, 0.0),
                b100A=self._f(self.A_b100L, 0.0), b100B=self._f(self.B_b100L, 0.0),
                hbA=self._f(self.A_hb, 0.0), hbB=self._f(self.B_hb, 0.0),
                ptsA=self._f(self.A_pts, required=True), ptsB=self._f(self.B_pts, required=True),
                shotsA=self._f(self.A_shots, required=True), shotsB=self._f(self.B_shots, required=True),
                totA=self._f(self.A_tot, 50.0), totB=self._f(self.B_tot, 50.0),
                w_pot=self.w_pot.get(), w_st=self.w_st.get(), w_b50=self.w_b50.get(), w_b100=self.w_b100.get(),
                w_hb=self.w_hb.get(), w_pts=self.w_pts.get(), w_shots=self.w_shots.get(), w_tot=self.w_tot.get(),
                sd_pot=self.sd_pot.get(), sd_st=self.sd_st.get(), sd_b50=self.sd_b50.get(), sd_b100=self.sd_b100.get(),
                sd_hb=self.sd_hb.get(), sd_pts_share=self.sd_ptsS.get(), sd_shots_share=self.sd_shS.get(), sd_tot_share=self.sd_totS.get(),
                k_shots=int(self.k_shots.get()), beta=self.beta.get()
            )

            # Per-frame probability from season + live
            total_logit = base_logit + boost
            p_frame_raw = inv_logit(total_logit)

            # Realism shrink toward 50–50
            lam = clip(self.lambda_shrink.get(), 0.0, 1.0)
            p_frame = 0.5 + lam * (p_frame_raw - 0.5)

            # Optional hard cap
            if self.cap_on.get():
                pmin = clip(self.pmin.get(), 0.0, 0.5)
                pmax = clip(self.pmax.get(), 0.5, 1.0)
                if pmin > pmax: pmin, pmax = pmax, pmin
                p_frame = clip(p_frame, pmin, pmax)

            # Score overlay → match probability
            bestof = self._f(self.bestof, required=True, to_int=True)
            a_won  = self._f(self.a_won, required=True, to_int=True)
            b_won  = self._f(self.b_won, required=True, to_int=True)
            target = bestof//2 + 1
            p_match = match_win_prob(p_frame, a_won, b_won, target)

            # Outputs
            self.out_p_frame.set(f"{p_frame:.3f}")
            self.out_o_frame.set(f"{1/max(1e-9,p_frame):.2f}")
            self.out_p_match.set(f"{p_match:.3f}")
            self.out_oA.set(f"{1/max(1e-9,p_match):.2f}")
            self.out_oB.set(f"{1/max(1e-9,1-p_match):.2f}")
            self.value_txt.set("")
            self.hint.set("")

        except ValueError:
            self.out_p_frame.set(""); self.out_o_frame.set("")
            self.out_p_match.set(""); self.out_oA.set(""); self.out_oB.set("")
            self.value_txt.set("")
            self.hint.set("Fill required Season + Live + Score fields and click Update.")

    def compare_value(self):
        try:
            p_match = float(self.out_p_match.get())
        except:
            self.value_txt.set("Click Update first.")
            return
        fairA = 1/max(1e-9,p_match)
        fairB = 1/max(1e-9,1-p_match)

        def edge(msg_label, book_str, fair):
            book_str = book_str.strip()
            if not book_str: return f"{msg_label}: —"
            try:
                b = float(book_str)
                e = (b - fair)/fair*100
                flag = "VALUE ✅" if e>2 else ("MARGINAL ⚠️" if -2<=e<=2 else "NO VALUE ❌")
                return f"{msg_label}: Fair {fair:.2f} vs Book {b:.2f} → Edge {e:+.1f}% {flag}"
            except:
                return f"{msg_label}: invalid odds"

        a_line = edge("Player A", self.bookA.get(), fairA)
        b_line = edge("Player B", self.bookB.get(), fairB)
        self.value_txt.set(a_line + "\n" + b_line)

if __name__ == "__main__":
    App().mainloop()
