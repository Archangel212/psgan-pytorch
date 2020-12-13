import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path
import re
import math

# experiments_name = "Batik_70_500by500_augmented/kernel=4,generator_leakyRelu=0.2,label_smoothing/train_log_20201127_19-34-03.csv"
# experiments_name = "/Users/mac/Deep_Learning/SinGAN/psgan-pytorch/log/Batik_500by500_homogenous_826-900/default_parameters/train_log_20201114_20-23-28.csv"
# df_csv = pd.read_csv(experiments_name, index_col=None)

# print(df_csv["total_loss"].mean(), df_csv["discriminator_loss"].mean(), df_csv["generator_loss"].mean())

std = 0.1
ln = 5
std_decay = std / (ln -1 )

for i in range(ln):
  print(std,std_decay)
  std = std - std_decay

# os.chdir("/Users/mac/Deep_Learning/SinGAN/psgan-pytorch/log")

# pths = [pth for pth in Path("/Users/mac/Deep_Learning/SinGAN/psgan-pytorch/log").rglob("*.pth")]

# new_pths = []
# for pth in pths:
#   if not (pth.match("generator_param_fin_10000.pth") or pth.match("generator_param_fin_20000.pth")):
#     print(pth)
#     new_pths.append(pth)
#     # os.remove(pth)

i = 160
k = 5
p = 2
s = 2

def zero_pad_output()


