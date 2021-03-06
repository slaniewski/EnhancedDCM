# Allows to run as main from any directory and import utility packages
if __name__ == "__main__" and __package__ is None:
    from sys import path
    from os.path import dirname as dir

    print(path[0])
    path.append(dir(path[0]))
    splits = path[0].split('/')

    parent = '/'.join(splits[:-3])
    path.append(dir(parent))
    parent = '/'.join(splits[:-2])
    path.append(dir(parent))
    parent = '/'.join(splits[:-1])
    path.append(dir(parent))
    __package__ = "generated_data"

import pickle
from EnhancedDCM.utilities import grad_hess_utilities as ghu
from keras.models import load_model
from swissmetro_paper import data_manager as dm
import numpy as np
from keras import backend as K


"""
    Saves in file and Writes results of all Models specified in "Cases" 
"""

def fetch_model(neuron, path, extend):
    filename = "{}swissmetro{}{}.h5".format(path, neuron, extend)
    return load_model(filename)


def get_inputs_labels(filePath, fileInputName, filePart, simpleArchitecture=False, lmnlArchitecture=False, write=False):
    inputs_labels, extra, _ = dm.keras_input(filePath, fileInputName, filePart, simpleArchitecture=simpleArchitecture,
                                             lmnlArchitecture=lmnlArchitecture, write=write)

    labels = inputs_labels[:, -1, :]
    inputs = np.delete(inputs_labels, -1, axis=1)
    inputs = np.expand_dims(inputs, -1)

    extra = np.expand_dims(extra, -1)
    extra = np.expand_dims(extra, -1)
    extra = (extra-extra.mean(axis=0))/extra.std(axis=0)
    return inputs, extra, labels


def scan_iteration(cases, paths_extends, filePath, fileInputBase, encyclopedia, std_flag=False):
    fileInputName = fileInputBase

    def get_model_inputs_labels(filePart):
        # Get model inputs for each .dat for Train and Test
        inputs, extra_input, labels = get_inputs_labels(filePath, fileInputName, filePart)
        inputs_simple, extra_input_simple, _ = get_inputs_labels(filePath, fileInputName, filePart,
                                                                 simpleArchitecture=True)
        inputs_lmnl, extra_input_lmnl, _ = get_inputs_labels(filePath, fileInputName, filePart, lmnlArchitecture=True)
        # Assign inputs to models
        model_inputs = {case: [inputs] for case in cases if 'FULL' in case}
        model_inputs.update({case: [inputs_simple] for case in cases if 'FULL' not in case})
        # MNL models have single input in Input layer
        model_inputs['HYBRID'] = [inputs_lmnl, extra_input_lmnl]
        model_inputs['HYBRID_NAIVE'] = [inputs, extra_input]
        model_inputs['HRUSCHKA'] = [inputs_simple[:,:,i:i+1] for i in range(inputs_simple.shape[2])]
        model_inputs['HRUSCHKA_FULL'] = [inputs[:,:,i:i+1] for i in range(inputs.shape[2])]
        model_inputs['HRUSCH07'] = [inputs_simple[:,:,i:i+1] for i in range(inputs_simple.shape[2])]
        model_inputs['HRUSCH07_FULL'] = [inputs[:,:,i:i+1] for i in range(inputs.shape[2])]
        # model_inputs[cases[2]] = [inputs]
        return model_inputs, labels

    model_inputs, train_labels = get_model_inputs_labels('_train')
    model_test_inputs, test_labels = get_model_inputs_labels('_test')
    # Dict to save all values and plotting
    encyclopedia = {}

    for case in cases:
        NN_flag = 'HRUSCHKA' in case
        # Get model extension name and path to .dat file
        path, extend = paths_extends[case]
        model = fetch_model('', path, extend)
        if not NN_flag:
            betas = ghu.get_betas(model)
        likelihood_train, accuracy_train = ghu.get_likelihood_accuracy(model, model_inputs[case], train_labels)
        likelihood_test, accuracy_test = ghu.get_likelihood_accuracy(model, model_test_inputs[case], test_labels)
        # Getting STD is slow (1-3s), avoid if possible
        if std_flag and not NN_flag:
            stds = ghu.get_stds(model, model_inputs[case], train_labels)
        if not NN_flag:
            encyclopedia['betas_' + case] = betas
        encyclopedia['likelihood_train_' + case] = likelihood_train
        encyclopedia['likelihood_test_' + case] = likelihood_test
        encyclopedia['accuracy_train_' + case] = accuracy_train
        encyclopedia['accuracy_test_' + case] = accuracy_test
        if std_flag and not NN_flag:
            encyclopedia['stds_' + case] = stds

    K.clear_session()
    return encyclopedia


if __name__ == '__main__':
    cases = [
        'MNL',
        'FULL_MNL',
        'HYBRID',
        'HYBRID_NAIVE',
        'HRUSCH07',
        'HRUSCH07_FULL',
        'HRUSCHKA',
        'HRUSCHKA_FULL',
    ]

    encyclopedia = {}

    paths_extends = {
        'MNL': ['../models/', '_MNL'],
        'FULL_MNL': ['../models/', '_MNL_Full'],
        'HYBRID': ['../models/', '_Enhancedextra'],
        'HYBRID_NAIVE': ['../models/', '_Enhanced_Naiveextra'],
        'HRUSCH07': ['../models/', '_Hruschka07'],
        'HRUSCH07_FULL': ['../models/', '_Hruschka07_Full'],
        'HRUSCHKA': ['../models/', '_Hruschka'],
        'HRUSCHKA_FULL': ['../models/', '_Hruschka_Full'],
    }

    filePath = '../models/'
    fileInputBase = 'swissmetro'

    encyclopedia = scan_iteration(cases, paths_extends, filePath, fileInputBase, encyclopedia, std_flag=True)

    pickle.dump(encyclopedia, open('Encyclopedia_.p', 'wb'))

    print('\n\n----- Likelihood Train set -----')
    for case in cases:
        likelihood = encyclopedia['likelihood_train_' + case]
        print(case + ': {}'.format(np.array(likelihood)))

    print('\n\n----- likelihood_test_ -----')
    for case in cases:
        likelihood = encyclopedia['likelihood_test_' + case] 
        print(case + ': {}'.format(np.array(likelihood)))

    print('\n\n----- Betas and Stds -----')
    for case in cases[:-2]:
        betas = encyclopedia['betas_' + case]
        stds = encyclopedia['stds_' + case]
        print('\n' + case + ': {}'.format(np.array(betas)))
        print('stds' + ': {}'.format(np.array(stds)))
        print('t-tests: {}'.format((np.array(betas)/np.array(stds))))
