import sys
from os import listdir
from collections import OrderedDict
from os.path import isfile, join, dirname, splitext
import operator
import re
import numpy as np

from converter import Shot, Diagram
def find_bounds(diagram, threshhold):
    n = len(diagram.x)
    l = -1
    r = -1
    for i in range(n):
        if diagram.y[i] > threshhold:
            l = diagram.x[i]
            break
    for i in reversed(range(n)):
        if diagram.y[i] > threshhold:
            r = diagram.x[i]
            break
    return l, r

def runningMean(x, N):
    y = np.zeros((len(x),))
    for ctr in range(len(x)):
         y[ctr] = np.sum(x[ctr:(ctr+N)])
    return y/N

def flux_delta(shot1, shot2, threshhold=200):

    Ip1 = shot1.get_diagram_for_name("Ip внутр")
    Ip1.y = runningMean(Ip1.y, 11)
    Ip2 = shot2.get_diagram_for_name("Ip внутр")
    Ip2.y = runningMean(Ip2.y, 11)
    l1, r1 = find_bounds(Ip1, threshhold)
    l2, r2 = find_bounds(Ip2, threshhold)
    l = max(l1, l2)
    r = min(r1, r2)
    if l >= r:
        return (-1, -1, -1)
    x = Ip1.x[np.searchsorted(Ip1.x, l): np.searchsorted(Ip1.x, r)]
    t1 = Ip1.for_x(x)
    t2 = Ip2.for_x(x)
    Ip = [(t1[i]-t2[i]) for i in range(len(x))]
    pos = 0
    for i in range(len(Ip)):
        if abs(Ip[i]) < abs(Ip[pos]):
            pos = i
    # print(pos)
    # print(len(Ip))
    # print(len(x))
    res_x = x[pos]
    #print("At point {}".format(res_x))
    Flux1 = shot1.get_diagram_for_name("Диамагнитный сигнал")
    #print(Flux1.for_x(res_x)[0])
    Flux1.y = runningMean(Flux1.y, 11)
    Flux2 = shot2.get_diagram_for_name("Диамагнитный сигнал")
    Flux2.y = runningMean(Flux2.y, 11)
    delta_flux = abs(Flux1.for_x(res_x)[0] - Flux2.for_x(res_x)[0])

    Nl1 = shot1.get_diagram_for_name("nl 42")
    Nl1.y = runningMean(Nl1.y, 11)
    Nl2 = shot2.get_diagram_for_name("nl 42")
    Nl2.y = runningMean(Nl2.y, 11)
    delta_n = abs(Nl1.for_x(res_x)[0] - Nl2.for_x(res_x)[0])
    #print(delta_flux)
    #print(delta_n)
    return delta_flux, delta_n, res_x


def check_nbi(shot):
    Eec = shot.get_diagram_for_name("Emission electrode current")
    Eec.y = runningMean(Eec.y, 11)
    val = max(Eec.y)
    l, r= find_bounds(Eec, val/2)
    if(r-l)/Eec.x[-1] < 0.5:
        return True
    else:
        return False

def build_flux_nl_dependency(names, threshold):
    shots_oh = []
    shots_nbi = []
    min_shot = None
    mv = None
    res = []
    ignored = 0
    for x in names:
        print("decompressing file: {}".format(x))
        shot = Shot(x)
        cv = min(shot.get_diagram_for_name("nl 42").y)
        if not mv or mv > cv:
            mv = cv
            min_shot = shot
        if check_nbi(shot):
            shots_nbi.append(shot)
            print("Itentified shot {} as NBI".format(x))
        else:
            shots_oh.append(shot)
            print("Itentified shot {} as OH".format(x))

    for shot in shots_nbi:
        if shot.file == min_shot.file:
            continue
        df, dn, x = flux_delta(shot, min_shot, threshhold=threshold)
        if df == -1 and dn == -1 and x == -1:
            ignored += 1
            continue
        print("Shots {} and {} have flux_delta at {} and n delta at {}".format(shot.file, min_shot.file, df, dn))
        res.append((df, dn, x, shot.file, 1))

    for shot in shots_oh:
        if shot.file == min_shot.file:
            continue
        df, dn, x = flux_delta(shot, min_shot, threshhold=threshold)
        if df == -1 and dn == -1 and x == -1:
            ignored += 1
            continue
        print("Shots {} and {} have flux_delta at {} and n delta at {}".format(shot.file, min_shot.file, df, dn))
        res.append((df, dn, x, shot.file, 0))

    print("Ignored {} files".format(ignored))
    return res




