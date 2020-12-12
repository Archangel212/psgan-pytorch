batik_dataset_name=dtd_honeycomb_dataset 
experiment_name=single_honeycomb_cardinal_dimensionality

python train.py --dataset $batik_dataset_name --save_dir ./log/$batik_dataset_name/$experiment_name --tqdm_notebook True

msg="Training ${batik_dataset_name} with ${experiment_name}"

git add --all
git commit -m "$msg"
git push 

echo "Finished" $msg

sudo poweroff
