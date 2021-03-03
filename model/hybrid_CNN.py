import torch
import torch.nn as nn
import torch.nn.functional as F

"""
You got a d-dim covaraite vector as input
K_l = W_0 + W_1 * S_l

S_0 = male (1)
S_1 = female (0)

So two kinds of kernels; we will have a certain number of each type.

TODO: get the covariate vector first.
 
for i, (images, labels) in enumerate(train_loader):
    labels = labels[:, 2] # attractiveness label

The rest is just tensor computation
"""

class Hybrid_Conv2d(nn.Module):
    def __init__(self, channel_in, channel_out, kernel_size, stride=1, padding=0):
        super(Hybrid_Conv2d, self).__init__()
        self.kernel_size = kernel_size
        self.channel_in = channel_in
        self.channel_out = channel_out
        self.stride = stride
        self.padding = padding
        
        self.w_0 = nn.Parameter(torch.randn(channel_out), requires_grad=True)
        self.w_1 = nn.Parameter(torch.randn(channel_out), requires_grad=True)
 
    def forward(self, x):
        
        w_0 = self.w_0
        w_1 = self.w_1
        out = F.conv2d(x, kernel, stride=self.stride, padding=self.padding)
        return out
        
        
########################################################################################
  
  
  
      
import torch.nn.functional as F
import torch

def gabor_fn(kernel_size, channel_in, channel_out, sigma, theta, Lambda, psi, gamma):
    sigma_x = sigma    # [channel_out]
    sigma_y = sigma.float() / gamma     # element-wize division, [channel_out]

    # Bounding box
    nstds = 3 # Number of standard deviation sigma
    xmax = kernel_size // 2
    ymax = kernel_size // 2
    xmin = -xmax
    ymin = -ymax
    ksize = xmax - xmin + 1
    y_0 = torch.arange(ymin, ymax+1)
    y = y_0.view(1, -1).repeat(channel_out, channel_in, ksize, 1).float()
    x_0 = torch.arange(xmin, xmax+1)
    x = x_0.view(-1, 1).repeat(channel_out, channel_in, 1, ksize).float()   # [channel_out, channelin, kernel, kernel]

    # Rotation
    # don't need to expand, use broadcasting, [64, 1, 1, 1] + [64, 3, 7, 7]
    x_theta = x * torch.cos(theta.view(-1, 1, 1, 1)) + y * torch.sin(theta.view(-1, 1, 1, 1))
    y_theta = -x * torch.sin(theta.view(-1, 1, 1, 1)) + y * torch.cos(theta.view(-1, 1, 1, 1))

    # [channel_out, channel_in, kernel, kernel]
    gb = torch.exp(-.5 * (x_theta ** 2 / sigma_x.view(-1, 1, 1, 1) ** 2 + y_theta ** 2 / sigma_y.view(-1, 1, 1, 1) ** 2)) \
         * torch.cos(2 * math.pi / Lambda.view(-1, 1, 1, 1) * x_theta + psi.view(-1, 1, 1, 1))

    return gb


class GaborConv2d(nn.Module):
    def __init__(self, channel_in, channel_out, kernel_size, stride=1, padding=0):
        super(GaborConv2d, self).__init__()
        self.kernel_size = kernel_size
        self.channel_in = channel_in
        self.channel_out = channel_out
        self.stride = stride
        self.padding = padding

        self.Lambda = nn.Parameter(torch.rand(channel_out), requires_grad=True)
        self.theta = nn.Parameter(torch.randn(channel_out) * 1.0, requires_grad=True)
        self.psi = nn.Parameter(torch.randn(channel_out) * 0.02, requires_grad=True)
        self.sigma = nn.Parameter(torch.randn(channel_out) * 1.0, requires_grad=True)
        self.gamma = nn.Parameter(torch.randn(channel_out) * 0.0, requires_grad=True)

        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        theta = self.sigmoid(self.theta) * math.pi * 2.0
        gamma = 1.0 + (self.gamma * 0.5)
        sigma = 0.1 + (self.sigmoid(self.sigma) * 0.4)
        Lambda = 0.001 + (self.sigmoid(self.Lambda) * 0.999)
        psi = self.psi

        kernel = gabor_fn(self.kernel_size, self.channel_in, self.channel_out, sigma, theta, Lambda, psi, gamma)
        kernel = kernel.float()   # [channel_out, channel_in, kernel, kernel]

        out = F.conv2d(x, kernel, stride=self.stride, padding=self.padding)

        return out
    
    
#############################################################

class Conv2d_symmetric(nn.Module):
    def __init__(self):
        super(Conv2d_simple, self).__init__()

        self.a = nn.Parameter(torch.randn(1))
        self.b = nn.Parameter(torch.randn(1))
        self.c = nn.Parameter(torch.randn(1))


        self.bias = None
        self.stride = 2
        self.padding = 1
        self.dilation = 1
        self.groups = 1



    def forward(self, input):

        #in case we use gpu we need to create the weight matrix there
        device = self.a.device

        weight = torch.zeros((1,1,3,3)).to(device)
        weight[0,0,0,0] += self.c[0]
        weight[0,0,0,1] += self.b[0]
        weight[0,0,0,2] += self.c[0]
        weight[0,0,1,0] += self.b[0]
        weight[0,0,1,1] += self.a[0]
        weight[0,0,1,2] += self.b[0]
        weight[0,0,2,0] += self.c[0]
        weight[0,0,2,1] += self.b[0]
        weight[0,0,2,2] += self.c[0]


        # print("weight= ", weight)
        # print("inout = ", input)
        return F.conv2d(input, weight, self.bias, self.stride,
                        self.padding, self.dilation, self.groups)