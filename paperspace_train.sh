batik_dataset_name=Batik_500by500_homogenous_736-900
experiment_name=kernel=4,generator_leakyRelu=0.2,instance_noise_mean=0_std=0.1,label_smoothing=0.0955percent,spatal_size=1

python train.py --dataset batik_dataset/$batik_dataset_name --save_dir ./log/$batik_dataset_name/$experiment_name --tqdm_notebook True

msg="Training ${batik_dataset_name} with ${experiment_name}"

git add --all
git commit -m "$msg"
git push 

echo "Finished" $msg

sudo poweroff