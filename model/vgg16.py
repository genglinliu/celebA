import torch
import torch.nn as nn
import torch.nn.functional as F

from model.hybrid_conv_multicovariate import Hybrid_Conv2d_v2


model_urls = {
    'vgg16': 'https://download.pytorch.org/models/vgg16-397923af.pth',
    'vgg16_bn': 'https://download.pytorch.org/models/vgg16_bn-6c64b313.pth'
}

model_path = {
    'vgg16': 'model/vgg16_pretrained.pth',
    'vgg16_bn': 'model/vgg16_bn_pretrained.pth'
}


class VGG(nn.Module):

    def __init__(self, features, num_classes=1000, init_weights=True): # change to binary classifier
        super(VGG, self).__init__()
        self.features = features
        self.avgpool = nn.AdaptiveAvgPool2d((7, 7))
        self.classifier = nn.Sequential(
            nn.Linear(512 * 7 * 7, 4096),
            nn.ReLU(True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(True),
            nn.Dropout(),
            nn.Linear(4096, num_classes),
        )
        if init_weights:
            self._initialize_weights()

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)


def make_layers(cfg, batch_norm=False):
    layers = []
    in_channels = 3
    for v in cfg:
        if v == 'M':
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
        else:
            conv2d = nn.Conv2d(in_channels, v, kernel_size=3, padding=1)
            if batch_norm:
                layers += [conv2d, nn.BatchNorm2d(v), nn.ReLU(inplace=True)]
            else:
                layers += [conv2d, nn.ReLU(inplace=True)]
            in_channels = v
    return nn.Sequential(*layers)

# M means MaxPool
cfg = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512, 'M', 512, 512, 512, 'M']


def _vgg(arch, cfg, batch_norm, pretrained, progress, **kwargs):
    if pretrained:
        kwargs['init_weights'] = False
    model = VGG(make_layers(cfg, batch_norm=batch_norm), **kwargs)
    if pretrained:
        state_dict = torch.load(model_path[arch])
        model.load_state_dict(state_dict)
    return model


def vgg16(pretrained=False, progress=True, **kwargs):
    """ (CUSTOMIZED) VGG 16-layer model (configuration "D")
    Takes in the cov paramter and forward function is customized
    `"Very Deep Convolutional Networks For Large-Scale Image Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
        progress (bool): If True, displays a progress bar of the download to stderr
    """
    return _vgg('vgg16', cfg, False, pretrained, progress, **kwargs)


def vgg16_bn(pretrained=False, progress=True, **kwargs):
    """ (CUSTOMIZED) VGG 16-layer model (configuration "D") with batch normalization
    `"Very Deep Convolutional Networks For Large-Scale Image Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_

    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
        progress (bool): If True, displays a progress bar of the download to stderr
    """
    return _vgg('vgg16_bn', cfg, True, pretrained, progress, **kwargs)



class HybridVGG16(nn.Module):
    """
    Hybrid Vgg16_bn network: A pretrained vgg16_bn with FIRST conv layer being a Hybrid_Conv2d layer
    
    """
    def __init__(self):
        super(HybridVGG16, self).__init__()
        # load pytorch vgg16 with pretrained weights
        vgg = vgg16_bn(pretrained=True)

        # set the three blocks you need for forward pass
        # remove the first conv layer + relu from the feature extractor
        self.features = vgg.features[1:]
        self.avgpool = vgg.avgpool
        self.classifier = vgg.classifier
        
        # hybrid layers
        # self.hybrid_conv = Hybrid_Conv2d(3, 64, kernel_size=(64, 3, 3, 3)) 
        self.hybrid_conv = Hybrid_Conv2d_v2(3, 64, kernel_size=(64, 3, 3, 3)) 
        
    # Set your own forward pass
    def forward(self, x, cov):
        x = self.hybrid_conv(x, cov)
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x



class HybridVGG16_v2(nn.Module):
    """
    Hybrid Vgg16_bn network: A pretrained vgg16_bn with SECOND conv layer (vgg.feature[3]) being a Hybrid_Conv2d layer
    confusing error: it gives None type in Logmax
    """
    def __init__(self):
        super(HybridVGG16_v2, self).__init__()
        # load pytorch vgg16 with pretrained weights
        vgg = vgg16_bn(pretrained=True)

        # set the three blocks you need for forward pass
        # remove the first conv layer + relu from the feature extractor
        self.features_1 = vgg.features[0:3] # layer 0, 1, 2
        self.features_2 = vgg.features[4:]
        self.avgpool = vgg.avgpool
        self.classifier = vgg.classifier
        
        # hybrid layer - to replace vgg.features[3]
        self.hybrid_conv = Hybrid_Conv2d_v2(64, 64, kernel_size=(64, 64, 3, 3)) 
        
    # Set your own forward pass
    def forward(self, x, cov):
        x = self.features_1(x)
        x = self.hybrid_conv(x, cov)
        x = self.features_2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return 
    
    
class HybridVGG16_v3(nn.Module):
    """
    Hybrid Vgg16_bn network: A pretrained vgg16_bn with THIRD conv layer (vgg.feature[7]) being a Hybrid_Conv2d layer
    """
    def __init__(self):
        super(HybridVGG16_v3, self).__init__()
        # load pytorch vgg16 with pretrained weights
        vgg = vgg16_bn(pretrained=True)

        # set the three blocks you need for forward pass
        # remove the first conv layer + relu from the feature extractor
        self.features_1 = vgg.features[0:7] # layers 0-6
        self.features_2 = vgg.features[8:]  # layers 
        self.avgpool = vgg.avgpool
        self.classifier = vgg.classifier
        
        # hybrid layer - to replace vgg.features[7]
        self.hybrid_conv = Hybrid_Conv2d_v2(64, 128, kernel_size=(128, 64, 3, 3)) 
        
    # Set your own forward pass
    def forward(self, x, cov):
        x = self.features_1(x)
        x = self.hybrid_conv(x, cov)
        x = self.features_2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x
    
    
class HybridVGG16_v10(nn.Module):
    """
    LateFused Hybrid Vgg16_bn network: A pretrained vgg16_bn with 5th conv layer (feature[14]) being a Hybrid_Conv2d layer
    """
    def __init__(self):
        super(HybridVGG16_v10, self).__init__()
        # load pytorch vgg16 with pretrained weights
        vgg = vgg16_bn(pretrained=True)

        # set the three blocks you need for forward pass
        # remove the first conv layer + relu from the feature extractor
        self.features_1 = vgg.features[0:14] # layers 0-39
        self.features_2 = vgg.features[15:]  # layers 
        self.avgpool = vgg.avgpool
        self.classifier = vgg.classifier
        
        # hybrid layer - to replace vgg.features[7]
        self.hybrid_conv = Hybrid_Conv2d_v2(128, 256, kernel_size=(256, 128, 3, 3)) 
        
    # Set your own forward pass
    def forward(self, x, cov):
        x = self.features_1(x)
        x = self.hybrid_conv(x, cov)
        x = self.features_2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x
    
class HybridVGG16_v40(nn.Module):
    """
    LateFused Hybrid Vgg16_bn network: A pretrained vgg16_bn with LAST conv layer (vgg.feature[40]) being a Hybrid_Conv2d layer
    """
    def __init__(self):
        super(HybridVGG16_v40, self).__init__()
        # load pytorch vgg16 with pretrained weights
        vgg = vgg16_bn(pretrained=True)

        # set the three blocks you need for forward pass
        # remove the first conv layer + relu from the feature extractor
        self.features_1 = vgg.features[0:40] # layers 0-39
        self.features_2 = vgg.features[41:]  # layers 
        self.avgpool = vgg.avgpool
        self.classifier = vgg.classifier
        
        # hybrid layer - to replace vgg.features[7]
        self.hybrid_conv = Hybrid_Conv2d_v2(512, 512, kernel_size=(512, 512, 3, 3)) 
        
    # Set your own forward pass
    def forward(self, x, cov):
        x = self.features_1(x)
        x = self.hybrid_conv(x, cov)
        x = self.features_2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x