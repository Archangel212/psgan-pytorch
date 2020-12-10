import os
import argparse
import random
import math
from datetime import datetime
import time

import torch 
import torch.nn as nn
import torch.nn.functional as F
import torchvision.utils as vutils
from torch.autograd import Variable


from model import PSGANGenerator as Generator
from model import PSGANDiscriminator as Discriminator

import dataset_setting
from data_loader import get_loader
from train_logger import TrainLogger

import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd

torch.backends.cudnn.benchmark = True

def save_image(imgs, output_dir="log", img_name="output", img_ext=".png"):
    vutils.save_image(imgs.data, "{}".format(os.path.join(output_dir, img_name+img_ext)))

def to_var(x, volatile=False, requires_grad=False):
  if torch.cuda.is_available() and not args.nogpu:
      x = x.cuda(args.gpu_device_num)
  return Variable(x, volatile=volatile, requires_grad=requires_grad)

def smooth_positive_labels(y, percentage=0.382):

  #randomize the label into range 0.7 to 1.2 according to GAN Hacks by S.Chintala
  unraveled_y = y.view(-1)
  len_unraveled_y = len(unraveled_y)
  amount = math.ceil(len_unraveled_y*percentage)
  random_idx = random.sample(range(len_unraveled_y), amount)

  for i in range(len(unraveled_y)):
    if i in random_idx:
      unraveled_y[i] = 1 - 0.3 + (random.random() * 0.5)

  return unraveled_y.view(y.shape)


def plot_loss(log_dir):
  plt.figure(figsize=(5,5))

  #find on csv file
  csv_path = [p for p in Path(log_dir).rglob("*.csv")][0]
  df = pd.read_csv(csv_path,index_col=None)

  plt.subplot(3,1,1)
  plt.plot(df["epoch"], df["total_loss"], color="g")
  plt.xlabel("epoch")
  plt.ylabel("total_loss")
  
  plt.subplot(3,1,2)
  plt.plot(df["epoch"], df["discriminator_loss"], color="b")
  plt.xlabel("epoch")
  plt.ylabel("discriminator_loss")
  
  plt.subplot(3,1,3)
  plt.plot(df["epoch"], df["generator_loss"], color="r")
  plt.xlabel("epoch")
  plt.ylabel("generator_loss")
  

  loss_path = os.path.join(log_dir, "loss_plot")
  os.makedirs(loss_path, exist_ok=True)

  plt.savefig(os.path.join(loss_path,"loss.jpg"))
  plt.close()

def train(args):

    if args.tqdm_notebook:
      # from tqdm import tqdm_notebook as tqdm
      from tqdm.notebook import tqdm
    else:
      from tqdm import tqdm
      
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    print("\nsaving at {}\n".format(args.save_dir))
    print("initializing...")

    # if args.layer_num is 5 and args.base_conv_channel is 64 then
    # gen_layer: [Z_dim, 512, 256, 128,  64, 3]
    # dis_layer: [    3,  64, 128, 256, 512, 1]
    gen_layers = [args.zl_dim+args.zg_dim+args.zp_dim]+[args.base_conv_channel*(2**(args.layer_num-n)) for n in range(2, args.layer_num+1)]+[3]
    dis_layers = [3]+[args.base_conv_channel*(2**n) for n in range(args.layer_num-1)]+[1]
    print("generator channels: ", gen_layers)
    print("discriminator channels: ", dis_layers)

    if torch.cuda.is_available() and not args.nogpu:
        generator = Generator(conv_channels=gen_layers,
                              kernel_size=args.kernel_size,
                              local_noise_dim=args.zl_dim,
                              global_noise_dim=args.zg_dim,
                              periodic_noise_dim=args.zp_dim,
                              spatial_size=args.spatial_size,
                              hidden_noise_dim=args.mlp_hidden_dim).cuda(args.gpu_device_num)
        discriminator = Discriminator(conv_channels=dis_layers, kernel_size=args.kernel_size).cuda(args.gpu_device_num)
    else:
        generator = Generator(conv_channels=gen_layers,
                              kernel_size=args.kernel_size,
                              local_noise_dim=args.zl_dim,
                              global_noise_dim=args.zg_dim,
                              periodic_noise_dim=args.zp_dim,
                              spatial_size=args.spatial_size,
                              hidden_noise_dim=args.mlp_hidden_dim)
        discriminator = Discriminator(conv_channels=dis_layers, kernel_size=args.kernel_size)

    if args.show_parameters:
        for idx, m in enumerate(model.modules()):
            print(idx, '->', m)

        print(args)

    # training setting
    if args.sgd:
        generator_optimizer = torch.optim.SGD(generator.parameters(), lr=args.learning_rate_g, momentum=0.9, weight_decay=1e-8)
        discriminator_optimizer = torch.optim.SGD(discriminator.parameters(), lr=args.learning_rate_g, momentum=0.9, weight_decay=1e-8)
    else:
        generator_optimizer = torch.optim.Adam(generator.parameters(), lr=args.learning_rate_d, weight_decay=1e-8, betas=(args.adam_beta, 0.999))
        discriminator_optimizer = torch.optim.Adam(discriminator.parameters(), lr=args.learning_rate_d, weight_decay=1e-8, betas=(args.adam_beta, 0.999))
    
    # for cropping size
    img_size = args.spatial_size*(2**args.layer_num)

    train_loader = get_loader(data_set=dataset_setting.get_train_loader(args, img_size),
                              batch_size=args.batch_size,
                              shuffle=True,
                              num_workers=args.num_workers)

    # for loggin the trainning
    tlog = TrainLogger("train_log", log_dir=args.save_dir, csv=True, header=True, suppress_err=False)
    tlog.disable_pickle_object()
    tlog.set_default_Keys(["epoch", "total_loss", "discriminator_loss", "generator_loss"])

    # output from discriminator is [0,1] of each patch, existing spatial_size*spatial_size number.
    true_label = torch.ones(args.batch_size, args.spatial_size*args.spatial_size)
    fake_label = torch.zeros(args.batch_size, args.spatial_size*args.spatial_size)

    true_label = smooth_positive_labels(true_label, percentage=0.0955)

    # for fixed sampling
    fixed_noise = to_var(generator.generate_noise(batch_size=8,
                                                  local_dim=args.zl_dim,
                                                  global_dim=args.zg_dim,
                                                  periodic_dim=args.zp_dim,
                                                  spatial_size=args.spatial_size,
                                                  tile=args.tile),
                        volatile=False)

    epochs = tqdm(range(args.epochs), ncols=100, desc="train")

    for epoch in epochs:
        # for logging
        epoch_total_loss = 0.0
        epoch_total_dloss = 0.0
        epoch_total_gloss = 0.0

        if (epoch+1) % args.decay_every == 0 and args.sgd:
            for param_group in generator_optimizer.param_groups:
                param_group['lr'] *= args.decay_value

            for param_group in discriminator_optimizer.param_groups:
                param_group['lr'] *= args.decay_value

            tqdm.write("decayed learning rate, factor {}".format(args.decay_value))

        _train_loader = tqdm(train_loader, ncols=100)


        std = 0.1
        #decaying std for every minibatch
        # std_decay = std / (train_loader.__len__() - 1)

        for images in _train_loader:
            batch_size = images.shape[0]

            images = images + torch.empty(images.shape).normal_(mean=0,std=std)

            # std = std - std_decay

            imgs = to_var(images, volatile=False)
            true_labels = to_var(true_label[:batch_size], volatile=False)
            fake_labels = to_var(fake_label[:batch_size], volatile=False)
            noise = generator.generate_noise(batch_size=batch_size,
                                                    local_dim=args.zl_dim,
                                                    global_dim=args.zg_dim,
                                                    periodic_dim=args.zp_dim,
                                                    spatial_size=args.spatial_size,
                                                    tile=args.tile)
            noise = to_var(noise)

            # generate fake image
            fake_img = generator(noise)

            # train discriminator ################################################################
            discriminator_optimizer.zero_grad()
            ########  train discriminator with real image    ########
            ######## ( Maximizing log(D(x))' ) ########
            discriminator_pred = discriminator(imgs)
            discriminator_true_loss = F.binary_cross_entropy(discriminator_pred, true_labels)

            epoch_total_loss += discriminator_true_loss.item()
            epoch_total_dloss += discriminator_true_loss.item()

            discriminator_true_loss.backward()

            ########  train discriminator with fake image      ########
            ######## ( Maximizing log(1-D(G(z))) ) ########
            discriminator_pred = discriminator(fake_img.detach())
            discriminator_fake_loss = F.binary_cross_entropy(discriminator_pred, fake_labels)

            epoch_total_loss += discriminator_fake_loss.item()
            epoch_total_dloss += discriminator_fake_loss.item()

            discriminator_fake_loss.backward()
            discriminator_optimizer.step()

            # train generator ####################################################################
            ######## ( Maximizing log(1-D(G(z))) ) ########
            generator_optimizer.zero_grad()

            fake_discriminate = discriminator(fake_img)
            generator_loss = F.binary_cross_entropy(fake_discriminate, true_labels)

            epoch_total_loss += generator_loss.item()
            epoch_total_gloss += generator_loss.item()

            generator_loss.backward()
            generator_optimizer.step()
            
            _train_loader.set_description("train[{}] dloss: {:.5f}, gloss: {:.5f}"
                         .format(args.save_dir, epoch_total_dloss, epoch_total_gloss))

        if (epoch+1) % args.save_sample_every == 0:
            generator.eval()
            # generate fake image
            fake_img = generator(fixed_noise)

            save_image(fake_img.mul(0.5).add(0.5).cpu(), output_dir=args.save_dir, img_name="sample_e{}".format(epoch+1))
            generator.train()

        tqdm.write("[#{}]train epoch dloss: {:.5f}, gloss: {:.5f}"
            .format(epoch+1, epoch_total_dloss, epoch_total_gloss))

        tlog.log([epoch+1, float(epoch_total_loss), float(epoch_total_dloss), float(epoch_total_gloss)])


    # saving training result
    generator.save(add_state={'optimizer_state_dict' : generator_optimizer.state_dict()},
               file_name=os.path.join(args.save_dir,'generator_param_fin_{}.pth'.format(epoch+1, datetime.now().strftime("%Y%m%d_%H-%M-%S"))))
    discriminator.save(add_state={'optimizer_state_dict' : discriminator_optimizer.state_dict()},
               file_name=os.path.join(args.save_dir,'discriminator_param_fin_{}.pth'.format(epoch+1, datetime.now().strftime("%Y%m%d_%H-%M-%S"))))

    plot_loss(args.save_dir)
    print("data is saved at {}".format(args.save_dir))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # settings
    parser.add_argument('--dataset', type=str, default='batik_dataset', help='directory of dataset')

    # detail settings
    parser.add_argument('--zl_dim', type=int, default=40, help='size of local part noise dimension')   # set default same as author's implementation
    parser.add_argument('--zg_dim', type=int, default=20, help='size of global part noise dimension')  # set default same as author's implementation
    parser.add_argument('--zp_dim', type=int, default=3, help='size of periodic part noise dimension') # set default same as author's implementation
    parser.add_argument('--mlp_hidden_dim', type=int, default=60, help='size of periodic part noise dimension')
    parser.add_argument('--spatial_size', type=int, default=4, help='size of spatial dimension')
    # for pytorch there is no pad="same", if you need use 5 or other sizes, you might need add torch.nn.functional.pad in the model.
    parser.add_argument('--kernel_size', type=int, default=4, help='size of kernels')
    parser.add_argument('--layer_num', type=int, default=5, help='number of layers')
    parser.add_argument('--base_conv_channel', type=int, default=64, help='base channel number of convolution layer')
    parser.add_argument('--tile', type=int, default=None, help='')

    parser.add_argument('--crop_size', type=int, default=64, help='size for image after processing') # setting same as pixel objectness
    # this time image size is depend on spatial dimension
    #parser.add_argument('--resize_size', type=int, default=80, help='size for image after processing')

    parser.add_argument('--save_dir', type=str, default="./log/", help='dir of saving log and model parameters and so on')
    parser.add_argument('--save_sample_every', type=int, default=500, help='count of saving model')
    parser.add_argument('--save_model_every', type=int, default=2500, help='count of saving model')

    parser.add_argument('--epochs', type=int, default=10000, help="train epoch num.")
    parser.add_argument('--batch_size', type=int, default=25, help="mini batch size")
    parser.add_argument('--num_workers', type=int, default=8, help="worker # of data loader")

    parser.add_argument('--learning_rate_g', type=float, default=2e-4, help="initial value of learning rate")
    parser.add_argument('--learning_rate_d', type=float, default=5e-5, help="initial value of learning rate")
    parser.add_argument('--adam_beta', type=float, default=0.5, help="initial value of learning rate")
    parser.add_argument('--decay_value', type=float, default=0.1, help="decay learning rate with count of args:decay_every in this factor.")
    parser.add_argument('--decay_every', type=int, default=2000, help="count of decaying learning rate")

    parser.add_argument('--gpu_device_num', type=int, default=0, help="device number of gpu")
        
    # option
    parser.add_argument('-nogpu', action="store_true", default=False, help="don't use gpu")
    parser.add_argument('-sgd', action="store_true", default=False, help="use sgd optimizer")
    parser.add_argument('-show_parameters', action="store_true", default=False, help='show model parameters')
    parser.add_argument('--tqdm_notebook', default=False, type=lambda x: (str(x).lower() == "true"), help='use tqdm for notebook')
    
    args = parser.parse_args()
    
    start = time.time()
    
    train(args)

    end = time.time()
    elapsed_time = end - start
    print("Time for training: {} seconds".format(elapsed_time))

