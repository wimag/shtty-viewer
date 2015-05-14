import sys
from os import listdir
from collections import OrderedDict
from os.path import isfile, join, dirname, splitext
import operator
import re
import numpy as np
from converter import Shot, Diagram

SMOOTHING = 11

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

def flux_delta(shot1, shot2, threshhold=200,nbi=False):

    Ip1 = shot1.get_diagram_for_name("Ip внутр")
    Ip1.y = runningMean(Ip1.y, SMOOTHING)
    Ip2 = shot2.get_diagram_for_name("Ip внутр")
    Ip2.y = runningMean(Ip2.y, SMOOTHING)
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
    print("min distance at {} with value {}".format(x[pos], Ip[pos]))
    print(Ip1.for_x(x[pos])[0])
    print(Ip2.for_x(x[pos])[0])
    # print(len(Ip))
    # print(len(x))
    res_x = x[pos]
    #print("At point {}".format(res_x))
    Flux1 = shot1.get_diagram_for_name("Диамагнитный сигнал")
    #print(Flux1.for_x(res_x)[0])
    Flux2 = shot2.get_diagram_for_name("Диамагнитный сигнал")
    for i in range(len(Flux1.y)):
        Flux1.y[i] -= Flux2.for_x(Flux1.x[i])[0]
    Flux1.y = runningMean(Flux1.y, SMOOTHING)
    delta_flux = abs(Flux1.for_x(res_x)[0])

    Nl1 = shot1.get_diagram_for_name("nl 42")
    Nl2 = shot2.get_diagram_for_name("nl 42")
    for i in range(len(Nl1.y)):
        Nl1.y[i] -= Nl2.for_x(Nl1.x[i])[0]
    Nl1.y = runningMean(Nl1.y, SMOOTHING)
    delta_n = abs(Nl1.for_x(res_x)[0])
    #print(delta_flux)
    #print(delta_n)
    return delta_flux, delta_n, res_x


def check_nbi(shot):
    Eec = shot.get_diagram_for_name("Emission electrode current")
    Eec.y = runningMean(Eec.y, 17)
    val = max(Eec.y)
    l, r= find_bounds(Eec, val/2)
    if(r-l)/Eec.x[-1] < 0.4:
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
        cv = shot.get_diagram_for_name("nl 42").bounded_max(0.12, 0.2)
        print("cv {}".format(cv))
        if cv < 17:
            continue
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
        print("Shots {} and {} have flux_delta at {} and n delta at {} at point t={}".format(shot.file, min_shot.file, df, dn, x))
        res.append(Point(t=x, file=shot.path, nbi=True, delta_flux=df, delta_n=dn))

    for shot in shots_oh:
        if shot.file == min_shot.file:
            continue
        df, dn, x = flux_delta(shot, min_shot, threshhold=threshold)
        if df == -1 and dn == -1 and x == -1:
            ignored += 1
            continue
        print("Shots {} and {} have flux_delta at {} and n delta at {} at point t={}".format(shot.file, min_shot.file, df, dn, x))

        res.append(Point(t=x, file=shot.path, nbi=False, delta_flux=df, delta_n=dn))

    print("Ignored {} files".format(ignored))
    return 'delta_n', 'delta_flux', res


def build_beta_density_dependency(names, threshold):
    xlabel, ylabel, points = build_flux_nl_dependency(names, threshold)
    new_points = []
    for point in points:
        R=36
        E_proc = 1.2
        E=1.9
        shot = Shot(point.file)
        Ip = shot.get_diagram_for_name('Ip внутр')
        Up = shot.get_diagram_for_name('Up (внутр')
        Up.y = runningMean(Up.y, SMOOTHING)
        Ip.y = runningMean(Ip.y, SMOOTHING)
        ip = Ip.for_x(point.t)[0]/1000000
        up = Up.for_x(point.t)[0]
        point.properties['ip'] = ip
        point.properties['up'] = up
        bt = 0.4
        import math
        beta = E_proc*bt*(point.properties['delta_flux']+0.1)/(2 * 3.15 * math.pi * ip * ip)
        point.properties['beta'] = beta
        new_points.append(point)
        print("beta {}".format(beta))
    return 'delta_n', 'beta', new_points

def build_tau_density_dependency(names, threshold):
    xlabel, ylabel, points = build_beta_density_dependency(names, threshold)
    new_points = []
    for point in points:
        R = 0.36
        a = 0.24
        k = 1.9
        print("shot ", point.file)
        ip = point.properties['ip']
        up = point.properties['up']
        print("up", up)
        p = ip*up
        print("p", p)
        n = point.properties['delta_n']
        e = (k*k)/(2*k)
        B = 0.4
        m = 2
        #ITER-98 scaling
        tau = 0.0562*(ip**0.93)*(B**0.15)*(n**0.41)*(p**(-0.69))*(R**1.97)*(k**0.78)*a*(e**0.58)*(m**0.19)
        print("tau", tau)

        point.properties['tau'] = tau
        if tau < 0.006:
            new_points.append(point)
    return 'delta_n', 'tau', new_points

class Point:
    def __init__(self, t=0, file=None, **kwargs):
        self.t = t
        self.file = file
        self.properties = {}
        for k, v in kwargs.items():
            self.properties[k] = v