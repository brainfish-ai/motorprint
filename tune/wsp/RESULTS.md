# WSP results (threshold = shipped 0.5)

Real-human FPR on 25168 test-user windows; catch rates on the EVAL half of held-out bot sessions (never used for design or fine-tuning).

| model | test_auc | real_fpr | heldout_eval_auc | catch_ghost | catch_wind | catch_agent | catch_replay | changed | changed_pct | gz |
|---|---|---|---|---|---|---|---|---|---|---|
| shipped (4_quant) | 0.9999 | 0.0033 | 0.9539 | 0.2092 | 0.9428 | 0.3316 | 0.2938 | 0 | 0.0% | 1703 |
| ft_masked_lr0.0003 | 0.9999 | 0.0404 | 0.9757 | 0.7564 | 0.9931 | 0.8051 | 0.6296 | 341 | 90.7% | 1705 |
| ft_masked_lr0.001 | 0.9998 | 0.0261 | 0.9878 | 0.8625 | 0.9908 | 0.7696 | 0.7704 | 341 | 90.7% | 1701 |
| ft_slot_lr0.0003 | 1.0000 | 0.0057 | 0.9667 | 0.4928 | 0.9680 | 0.5620 | 0.4321 | 40 | 10.6% | 1756 |
| ft_slot_lr0.001 | 1.0000 | 0.0097 | 0.9715 | 0.5745 | 0.9771 | 0.6608 | 0.5111 | 40 | 10.6% | 1757 |
| wsp | 0.9999 | 0.0033 | 0.9712 | 0.4327 | 0.9428 | 0.3316 | 0.4568 | 9 | 2.4% | 1722 |

Per-dataset real-human FPR (test users):

| model | adserp | boun | cmu | dux | keyrecs | mousetask |
|---|---|---|---|---|---|---|
| shipped (4_quant) | 0.0018 | 0.0000 | 0.0000 | 0.0051 | 0.0073 | 0.0000 |
| ft_masked_lr0.0003 | 0.0614 | 0.0154 | 0.0498 | 0.0398 | 0.0514 | 0.0000 |
| ft_masked_lr0.001 | 0.0169 | 0.0131 | 0.0353 | 0.0304 | 0.0403 | 0.0000 |
| ft_slot_lr0.0003 | 0.0080 | 0.0000 | 0.0000 | 0.0088 | 0.0102 | 0.0000 |
| ft_slot_lr0.001 | 0.0100 | 0.0011 | 0.0017 | 0.0145 | 0.0182 | 0.0000 |
| wsp | 0.0018 | 0.0000 | 0.0000 | 0.0051 | 0.0073 | 0.0000 |

Matched-FPR view: threshold re-picked on validation users so val real FPR = 0.0013 (shipped value), then scored on test users / eval half:

| model | thr | real_fpr (test) | ghost | wind | agent | replay | heldout_eval_auc |
|---|---|---|---|---|---|---|---|
| shipped (4_quant) | 0.491 | 0.0033 | 0.2135 | 0.9428 | 0.3367 | 0.2938 | 0.9539 |
| ft_masked_lr0.0003 | 0.982 | 0.0035 | 0.5000 | 0.9634 | 0.5848 | 0.4247 | 0.9757 |
| ft_masked_lr0.001 | 0.936 | 0.0041 | 0.6060 | 0.9794 | 0.6633 | 0.5778 | 0.9878 |
| ft_slot_lr0.0003 | 0.728 | 0.0032 | 0.4327 | 0.9497 | 0.4456 | 0.3778 | 0.9667 |
| ft_slot_lr0.001 | 0.879 | 0.0037 | 0.4871 | 0.9703 | 0.5747 | 0.4444 | 0.9715 |
| wsp | 0.491 | 0.0033 | 0.4355 | 0.9428 | 0.3367 | 0.4568 | 0.9712 |
