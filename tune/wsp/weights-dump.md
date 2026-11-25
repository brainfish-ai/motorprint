# motorprint shipped model: raw weights

38 inputs (standardised features, z-scores; `off` = ['wheel_dy_cv', 'click_offset']), 32 ReLU -> 16 ReLU -> 1 logit. int8 per-row, dequantised below.

## Layer 1 (feature -> h1_j). Nonzero incoming weights, largest first

- **h1_0** b=+0.47 | press_cv -0.43, hold_ms -0.41, turn_zero_frac -0.39, dt_mean -0.31, dt_mode_share +0.28, scroll_no_input_frac +0.23, peak_pos -0.20, hold_cv -0.18, jerk_mean +0.18, accel_mean +0.15, iki_mean -0.14, has_keys -0.13, untrusted_frac -0.12, moves_before_press +0.11, still_before_press +0.11, turn_mean +0.11, click_no_press_frac -0.11, press_ms -0.08, speed_cv -0.07, end_speed_ratio -0.03, has_scroll +0.02, speed_mean -0.00 | feeds h2 with |w|sum=1.67
- h1_1: dead (in=0 nonzero, out-use=0.00)
- h1_2: dead (in=0 nonzero, out-use=0.00)
- h1_3: dead (in=0 nonzero, out-use=0.00)
- h1_4: dead (in=0 nonzero, out-use=0.00)
- h1_5: dead (in=0 nonzero, out-use=0.00)
- **h1_6** b=-0.74 | iki_cv -0.57, hold_ms -0.53, iki_mean +0.36, turn_mean -0.29, max_dev -0.28, step_cv -0.28, dt_mean +0.25, event_rate +0.24, dt_mode_share +0.22, jerk_mean -0.18, has_keys +0.18, has_scroll -0.17, accel_mean -0.16, has_click +0.16, dt_cv -0.11, turn_entropy -0.11, hold_cv +0.10, moves_before_press +0.10, still_before_press +0.10, speed_cv -0.09, wheel_dt_cv -0.09, scroll_no_input_frac -0.09, has_mouse -0.09, n_moves -0.08, press_cv -0.07, pause_frac -0.07, untrusted_frac +0.06, peak_pos -0.05, press_ms -0.05, end_speed_ratio -0.04 | feeds h2 with |w|sum=2.27
- h1_7: dead (in=0 nonzero, out-use=0.00)
- h1_8: dead (in=0 nonzero, out-use=0.00)
- h1_9: dead (in=0 nonzero, out-use=0.00)
- h1_10: dead (in=0 nonzero, out-use=0.00)
- h1_11: dead (in=0 nonzero, out-use=0.00)
- h1_12: dead (in=5 nonzero, out-use=0.00)
- **h1_13** b=-0.64 | has_scroll +0.61, iki_cv +0.41, dt_cv -0.40, has_click +0.39, dt_mean +0.38, has_keys +0.34, speed_mean +0.30, moves_before_press +0.29, scroll_no_input_frac +0.27, dt_mode_share -0.27, max_dev -0.25, hold_ms +0.23, speed_cv +0.22, straightness +0.18, jerk_mean -0.17, step_cv -0.16, iki_mean +0.14, end_speed_ratio +0.14, has_mouse -0.08, press_cv +0.08, pause_frac -0.07, turn_entropy -0.06, dt_sub4_frac +0.06, untrusted_frac +0.06, peak_pos +0.05, still_before_press +0.04, click_no_press_frac -0.04, press_ms -0.04 | feeds h2 with |w|sum=2.29
- h1_14: dead (in=0 nonzero, out-use=0.02)
- h1_15: dead (in=0 nonzero, out-use=0.06)
- **h1_16** b=+0.09 | event_rate -0.87, hold_cv +0.42, hold_ms +0.40, iki_cv -0.30, press_ms +0.30, jerk_mean +0.26, still_before_press +0.23, speed_mean -0.18, dt_cv +0.18, dt_mean -0.17, n_moves +0.14, accel_mean +0.14, scroll_no_input_frac -0.10, pause_frac +0.10, speed_cv +0.10, has_keys -0.10, has_scroll +0.10, untrusted_frac -0.10, step_cv +0.09, dt_mode_share +0.08, press_cv -0.08, turn_mean -0.08, wheel_dt_cv -0.08, moves_before_press -0.07, has_click -0.06, click_no_press_frac +0.05, max_dev +0.02, turn_entropy +0.01 | feeds h2 with |w|sum=2.66
- **h1_17** b=+0.74 | dt_mode_share +0.22, has_scroll -0.18, n_moves +0.17, dt_cv +0.16, turn_entropy +0.15, iki_cv -0.15, scroll_no_input_frac +0.14, press_ms +0.14, wheel_dt_cv -0.14, dt_mean -0.13, hold_ms -0.13, turn_mean +0.13, jerk_mean +0.12, still_before_press +0.11, end_speed_ratio +0.11, max_dev +0.11, has_keys -0.10, has_mouse +0.09, event_rate +0.09, accel_mean +0.08, click_no_press_frac +0.06, iki_mean -0.06, press_cv +0.06, speed_cv -0.06, turn_zero_frac -0.02 | feeds h2 with |w|sum=1.14
- **h1_18** b=+0.28 | hold_ms -0.29, moves_before_press -0.26, turn_zero_frac +0.23, iki_mean -0.21, has_keys -0.21, scroll_no_input_frac -0.19, turn_entropy -0.18, event_rate +0.18, dt_cv +0.17, has_click -0.16, jerk_mean -0.15, n_moves -0.14, wheel_dt_cv +0.14, speed_mean -0.14, step_cv +0.13, accel_mean -0.13, press_ms -0.13, press_cv -0.12, pause_frac +0.11, hold_cv -0.10, still_before_press -0.09, turn_mean +0.08, iki_cv -0.05, end_speed_ratio +0.04, untrusted_frac -0.04, max_dev -0.04, peak_pos -0.01 | feeds h2 with |w|sum=1.82
- h1_19: dead (in=0 nonzero, out-use=0.00)
- h1_20: dead (in=0 nonzero, out-use=0.00)
- h1_21: dead (in=0 nonzero, out-use=0.00)
- **h1_22** b=-0.70 | dt_mean +0.50, iki_cv +0.38, speed_cv +0.30, hold_ms +0.26, has_keys +0.25, step_cv +0.25, speed_mean +0.23, has_click +0.20, jerk_mean -0.20, dt_cv -0.20, dt_mode_share +0.19, turn_zero_frac +0.18, max_dev -0.17, iki_mean +0.16, straightness +0.15, pause_frac -0.13, moves_before_press +0.13, turn_mean +0.12, wheel_dt_cv -0.12, still_before_press +0.11, press_cv -0.08, dt_sub4_frac +0.08, hold_cv +0.07, event_rate +0.06, n_moves -0.05, click_no_press_frac -0.04 | feeds h2 with |w|sum=2.30
- h1_23: dead (in=0 nonzero, out-use=0.00)
- h1_24: dead (in=0 nonzero, out-use=0.00)
- **h1_25** b=-0.36 | hold_ms +1.52, iki_cv +0.72, event_rate -0.49, iki_mean -0.26, dt_cv +0.20, moves_before_press -0.18, step_cv +0.18, max_dev +0.17, pause_frac +0.16, dt_mean -0.16, still_before_press +0.13, dt_mode_share +0.13, turn_entropy +0.13, jerk_mean +0.13, has_keys -0.13, has_click -0.13, accel_mean +0.11, straightness -0.11, end_speed_ratio -0.10, dt_sub4_frac -0.10, n_moves +0.08, input_no_key_frac +0.07, click_no_press_frac +0.06, speed_cv +0.06, wheel_dt_cv -0.06, press_cv -0.06, hold_cv -0.05, press_ms +0.05, has_scroll -0.02 | feeds h2 with |w|sum=3.93
- h1_26: dead (in=0 nonzero, out-use=0.00)
- h1_27: dead (in=1 nonzero, out-use=0.00)
- **h1_28** b=-0.76 | iki_cv -1.01, step_cv -0.92, turn_mean -0.82, hold_ms -0.74, iki_mean +0.55, pause_frac -0.32, has_keys +0.32, dt_mean +0.28, hold_cv +0.27, max_dev -0.25, speed_mean -0.24, untrusted_frac +0.22, speed_cv -0.20, event_rate +0.19, dt_cv -0.18, n_moves +0.18, turn_zero_frac -0.16, turn_entropy +0.13, press_ms -0.10, dt_mode_share -0.10, peak_pos +0.09, straightness +0.07, moves_before_press +0.06, input_no_key_frac -0.06, has_click +0.06, has_scroll -0.06, still_before_press -0.03, jerk_mean +0.02 | feeds h2 with |w|sum=3.91
- h1_29: dead (in=0 nonzero, out-use=0.00)
- h1_30: dead (in=0 nonzero, out-use=0.00)
- h1_31: dead (in=0 nonzero, out-use=0.00)

## Layer 2 (h1 -> h2_k)

- **h2_0** b=-0.11 out=+0.00 | 
- **h2_1** b=-0.24 out=+0.00 | 
- **h2_2** b=+1.36 out=-1.80 | h1_25 +0.97, h1_28 -0.70, h1_16 +0.65, h1_18 +0.54, h1_6 -0.51, h1_22 -0.46, h1_17 +0.44, h1_13 -0.44, h1_0 +0.36
- **h2_3** b=+0.28 out=+0.84 | h1_28 +0.45, h1_25 -0.40, h1_13 +0.29, h1_16 -0.28, h1_22 +0.27, h1_6 +0.22, h1_18 -0.21, h1_0 -0.16, h1_17 -0.07
- **h2_4** b=-0.28 out=+0.00 | 
- **h2_5** b=+0.50 out=-0.52 | h1_25 +0.27, h1_28 -0.25, h1_16 +0.17, h1_6 -0.16, h1_18 +0.14, h1_22 -0.14, h1_13 -0.13, h1_17 +0.12
- **h2_6** b=+0.27 out=-0.26 | h1_28 -0.13, h1_25 +0.13, h1_6 -0.08, h1_16 +0.08, h1_13 -0.07, h1_18 +0.07, h1_22 -0.06, h1_17 +0.06
- **h2_7** b=-0.08 out=+0.00 | 
- **h2_8** b=+0.09 out=+1.33 | h1_28 +0.72, h1_25 -0.59, h1_0 -0.52, h1_22 +0.44, h1_16 -0.41, h1_13 +0.40, h1_6 +0.37, h1_18 -0.19, h1_15 +0.03
- **h2_9** b=+0.06 out=+0.00 | 
- **h2_10** b=+0.10 out=+1.63 | h1_28 +0.87, h1_25 -0.72, h1_0 -0.63, h1_22 +0.53, h1_16 -0.50, h1_13 +0.50, h1_6 +0.45, h1_18 -0.23, h1_17 -0.06, h1_15 +0.03, h1_14 +0.02
- **h2_11** b=-0.15 out=+0.00 | 
- **h2_12** b=+0.67 out=-0.67 | h1_28 -0.35, h1_25 +0.34, h1_16 +0.22, h1_6 -0.20, h1_13 -0.20, h1_18 +0.17, h1_22 -0.17, h1_17 +0.15
- **h2_13** b=+0.81 out=-0.95 | h1_25 +0.50, h1_28 -0.43, h1_16 +0.33, h1_6 -0.27, h1_13 -0.26, h1_18 +0.25, h1_17 +0.24, h1_22 -0.23
- **h2_14** b=-0.19 out=+0.00 | 
- **h2_15** b=-0.01 out=+0.00 | 

## Output: b=-0.64

