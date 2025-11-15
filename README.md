Here is a **clean, polished GitHub README.md** for your **Snooker In-Play — Match Odds (Season + Live + Score)** model.
I included **your screenshot** (the one you just provided) properly embedded in Markdown.

If you want a version **without the screenshot**, just say.

---

# **Snooker In-Play — Match Odds (Season + Live + Score) [Realism]**

A high-precision **in-play snooker probability model** combining:

* **Season-long strength ratings**
* **Live in-match performance metrics**
* **Current match score overlay**
* **Realism guards, shrinkage & caps**
* **Dynamic DP race model** (frame-by-frame Bernoulli to match win probability)
* **Pre-match odds inversion** for prior strength
* **Value finder vs bookmaker odds**
* **Dark-themed Tkinter GUI (scrollable)**

This model is designed for live snooker betting—especially **Match Winner** markets—where both season form and in-play performance must be blended properly without overreacting to small samples.

---

## 📸 Screenshot

<img width="1175" height="1049" alt="image" src="https://github.com/user-attachments/assets/643997a8-3cf0-41b8-a3d6-ae1d77f3d951" />


---

## ⭐ Core Features

### 🎯 **1. Season Strength Model**

The left-hand panel computes a **season strength index** from:

* Points scored
* Matches played
* Win rate
* Average shot time
* 50+ breaks
* 100+ breaks

With configurable **weights**:

* Win rate
* Points per match
* 50+ per match
* 100+ per match
* Shot time
* Global season strength scale

This produces:

```
SeasonStrength = scale * (weighted combination of deviations vs soft league averages)
```

---

### 🔥 **2. Live Boost Model (In-Play Performance)**

The middle panel captures in-play data:

* Pot %
* Average shot time
* 50+ and 100+ counts
* Highest break
* Points
* Shots taken
* Time-on-table share

These feed a **live boost** applied directly in **logit space**, weighted and normalised by:

* Standard deviations (SD sliders)
* Reliability scaling via total shots (`k_shots`)
* Global β scaling
* Automatic clipping of z-scores to ±3

This ensures the model reacts **only when enough shots have occurred**.

---

### 🧠 **3. Realism Guards**

The model includes:

* Logit shrinkage toward 50–50 (`lambda_shrink`)
* Optional signal caps (`pmin`, `pmax`)
* Prior/frame blending via equivalent-frames strength (`n₀`)
* Season + Live → Signal → Prior blend

Final per-frame probability:

```
p_frame = inv_logit( w_prior*logit(p_prior) + w_signal*logit(p_signal) )
```

Where:

* `w_prior = n₀ / (n₀ + total_shots)`
* `w_signal = 1 – w_prior`

---

### 🏆 **4. Dynamic Match Probability (DP Race Model)**

A recursive dynamic-programming model computes:

```
P(match | per-frame p, score A-B, target frames)
```

Supporting best-of:

* 7
* 11
* 19
* Custom values

---

### 💷 **5. Value Comparison vs Book Odds**

The right-hand panel:

* Shows fair match odds for both players
* Accepts bookmaker decimal odds
* Computes edges:

  * **VALUE** (edge > +2%)
  * **MARGINAL**
  * **NO VALUE**

---

## 🖥️ GUI Layout (Scroll-Enabled)

* **Left**: Season form inputs + weights
* **Middle**: Live match stats + SDs + reliability
* **Right**:

  * Score inputs
  * Fair prices
  * Pre-match odds → prior conversion
  * Bookmaker price comparison
  * Update button

Fully scrollable via mouse wheel, including Linux support.

---

## 📦 Requirements

```
Python 3.9+
tkinter
math
```

No external dependencies.

Tkinter install on Linux:

```bash
sudo apt install python3-tk
```

---

## ▶️ Running the Model

```
python3 snooker_inplay.py
```

The GUI opens immediately.

* Fill **Season**, **Live**, and **Score** fields
* Click **Update**
* Optionally enter bookmaker odds
* Click **Compare Value**

---

## 🧮 Mathematical Summary

### Season Strength

Weighted linear model around league-centred baseline.

### Live Boost

Z-scored differences across performance metrics:

```
boost = β * w_rel * Σ ( weight_i * z_i )
```

### Total Signal

```
logit_signal = season_strength_diff + live_boost
p_signal = inv_logit(logit_signal)
```

### Prior Blend

From bookmaker pre-match odds:

```
implied_match_prob → invert via binary search → per-frame prior
```

Final per-frame estimate:

```
p_frame = inv_logit( w_prior*logit(p_prior) + w_signal*logit(p_signal) )
```

### DP Race Model

```
P(match) = p_frame * P(a+1,b) + (1 - p_frame)*P(a,b+1)
```

Memoised for speed.

---

## 📚 File Structure

```
snooker_inplay.py
README.md
```

---

## 🔧 Optional Extensions (I can add these)

* Charting of per-frame probability over time
* Export fair odds to CSV
* Monte Carlo version of frame-level variance
* Tracking of live edges over time
* Adding a “confidence meter” for bet sizing
* Automatic parsing of screenshots (season & match tabs)
* Integrating Betfair streaming prices


