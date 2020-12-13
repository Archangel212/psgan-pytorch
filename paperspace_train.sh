batik_dataset_name=Batik_70_500by500_augmented
experiment_name=kernel=4,generator_leakyRelu=0.2,instance_noise_mean=0_std=0.1,label_smoothing=0.0955percent,zl_dim=60,learning_rate_g=1e-4,learning_rate_d=4e-4

python train.py --dataset batik_dataset/$batik_dataset_name --save_dir ./log/$batik_dataset_name/$experiment_name --tqdm_notebook True

msg="Training ${batik_dataset_name} with ${experiment_name}"

git add --all
git commit -m "$msg"
git push 

echo "Finished" $msg

sudo poweroff