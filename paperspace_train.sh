batik_dataset_name=Batik_70_500by500_augmented
experiment_name=kernel=4,generator_leakyRelu=0.2,instance_noise_mean=0_std=0.1,label_smoothing=0.0955percent,zl_dim=60,zg_dim=60,learning_rate_g=1e-4,learning_rate_d=4e-4,d_dropout_lastlayer=0.2,bce_with_logits
# experiment_name=kernel=4,generator_leakyRelu=0.2,instance_noise_mean=0_std=0.1,label_smoothing=0.0955percent,learning_rate_g=1e-4,learning_rate_d=4e-4

python train.py --dataset batik_dataset/$batik_dataset_name --save_dir ./log/$batik_dataset_name/$experiment_name --tqdm_notebook True >> ./log/$batik_dataset_name/$experiment_name.txt


#tail the log to get time lapse
cat ./log/$batik_dataset_name/$experiment_name.txt | tail -20 > "./log/$batik_dataset_name/$experiment_name/$experiment_name.txt"
rm ./log/$batik_dataset_name/$experiment_name.txt

#change log from txt to jpg format
soffice --convert-to jpg ./log/$batik_dataset_name/$experiment_name/$experiment_name.txt --outdir ./log/$batik_dataset_name/$experiment_name/

msg="Training ${batik_dataset_name} with ${experiment_name}"

git add --all
git commit -m "$msg"
git push 

echo "Finished" $msg

sudo poweroff
