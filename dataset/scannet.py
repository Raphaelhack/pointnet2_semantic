import os
import sys
ROOT_DIR = os.path.abspath(os.path.pardir)
sys.path.append(ROOT_DIR)
import numpy as np
import pickle
import utils.pc_util as pc_util
import utils.scene_util as scene_util

# Dataset global parameters

NUM_CLASSES = 21

DATA_PATH = "dataset/scannet_data/"

FILENAME_TRAIN = 'scannet_train.pickle'
FILENAME_TEST = 'scannet_test.pickle'

LABELS_NAMES = ['unannotated', 'wall', 'floor', 'chair', 'table', 'desk', 'bed', 
'bookshelf', 'sofa', 'sink', 'bathtub', 'toilet', 'curtain', 'counter', 
'door', 'window', 'shower curtain', 'refridgerator', 'picture', 'cabinet', 'otherfurniture']

class Dataset():
    def __init__(self, npoints=8192, split='train'):
        self.npoints = npoints
        self.split = split

        # Load data
        if split=='train':
            self.data_filename = os.path.join(DATA_PATH, FILENAME_TRAIN)
        elif split=='test':
            self.data_filename = os.path.join(DATA_PATH, FILENAME_TEST)
        with open(self.data_filename,'rb') as fp:
            self.scene_points_list = pickle.load(fp)
            self.semantic_labels_list = pickle.load(fp)
        
        # Initialize weights
        if split=='train':
            labelweights = np.zeros(21)
            for seg in self.semantic_labels_list:
                tmp,_ = np.histogram(seg,range(22))
                labelweights += tmp
            labelweights = labelweights.astype(np.float32)
            labelweights = labelweights/np.sum(labelweights)
            self.labelweights = 1/np.log(1.2+labelweights)
        elif split=='test':
            self.labelweights = np.ones(21)
    
    def __getitem__(self, index):
        point_set = self.scene_points_list[index]
        semantic_seg = self.semantic_labels_list[index].astype(np.int32)
        coordmax = np.max(point_set,axis=0)
        coordmin = np.min(point_set,axis=0)
        smpmin = np.maximum(coordmax-[1.5,1.5,3.0], coordmin)
        smpmin[2] = coordmin[2]
        smpsz = np.minimum(coordmax-smpmin,[1.5,1.5,3.0])
        smpsz[2] = coordmax[2]-coordmin[2]
        isvalid = False
        for i in range(10):
            curcenter = point_set[np.random.choice(len(semantic_seg),1)[0],:]
            curmin = curcenter-[0.75,0.75,1.5]
            curmax = curcenter+[0.75,0.75,1.5]
            curmin[2] = coordmin[2]
            curmax[2] = coordmax[2]
            curchoice = np.sum((point_set>=(curmin-0.2))*(point_set<=(curmax+0.2)),axis=1)==3
            cur_point_set = point_set[curchoice,:]
            cur_semantic_seg = semantic_seg[curchoice]
            if len(cur_semantic_seg)==0:
                continue
            mask = np.sum((cur_point_set>=(curmin-0.01))*(cur_point_set<=(curmax+0.01)),axis=1)==3
            vidx = np.ceil((cur_point_set[mask,:]-curmin)/(curmax-curmin)*[31.0,31.0,62.0])
            vidx = np.unique(vidx[:,0]*31.0*62.0+vidx[:,1]*62.0+vidx[:,2])
            isvalid = np.sum(cur_semantic_seg>0)/len(cur_semantic_seg)>=0.7 and len(vidx)/31.0/31.0/62.0>=0.02
            if isvalid:
                break
        choice = np.random.choice(len(cur_semantic_seg), self.npoints, replace=True)
        point_set = cur_point_set[choice,:]
        semantic_seg = cur_semantic_seg[choice]      
        mask = mask[choice]
        sample_weight = self.labelweights[semantic_seg]
        sample_weight *= mask
        return point_set, semantic_seg, sample_weight
    
    def __len__(self):
        return len(self.scene_points_list)
