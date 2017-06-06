#!/usr/bin/python

import scipy
from scipy import stats
import numpy as np
from math import sqrt, asin, cos, sin, atan2
import networkx as nx
from gym_navigation_2d.envs.env_utils import *
from gym_navigation_2d.envs.geometry_utils import *
import sys
import pickle

<<<<<<< HEAD
class Obstacle(object):
    def __init__(self, c, w, h):
        self.rectangle_centers = [c]
        self.rectangle_widths = [w]
        self.rectangle_heights = [h]
        self.lowest_point = np.array([c[0], c[1] - h/2.0])
        self.representative_point = np.array([c[0], c[1]]) 
        
    def append(self, ca, wa, ha):
        self.rectangle_centers.append(ca)
        self.rectangle_widths.append(wa)
        self.rectangle_heights.append(ha)

        if (self.lowest_point[1] > ca[1] - ha/2.0):
            self.lowest_point = np.array([ca[0], ca[1] - ha/2.0])

    def merge(self, obs):
        self.rectangle_centers.extend(obs.rectangle_centers)
        self.rectangle_widths.extend(obs.rectangle_widths)
        self.rectangle_heights.extend(obs.rectangle_heights)

        for ca, wa, ha in zip(obs.rectangle_centers, obs.rectangle_widths, obs.rectangle_heights):
            if (self.lowest_point[1] > ca[1] - ha/2.0):
                self.lowest_point = np.array([ca[0], ca[1] - ha/2.0])

    def distance_to_point(self, x, y):
        p = np.array([x,y])
        dist = [point_to_rectangle_distance(p, ca, wa, ha) for ca,wa,ha in zip(self.rectangle_centers, self.rectangle_widths, self.rectangle_heights)]
        return min(dist)
    
    def distance_to_rectangle(self, ca, wa, ha):
        dist = [rectangle_to_rectangle_distance(ca, cb, wa, wb, ha, hb) for cb,wb,hb in zip(self.rectangle_centers, self.rectangle_widths, self.rectangle_heights)]
        return min(dist)

    def distance_to_obstacle(self, obs):
        dist = [self.distance_to_rectangle(ca, wa, ha) for ca,wa,ha in zip(obs.rectangle_centers, obs.rectangle_widths, obs.rectangle_heights)]
        return min(dist)

    def closest_point_to(self, p):
        closest_points_to_segments = [closest_point_on_segment(p, s, t) for c,w,h in zip(self.rectangle_centers, self.rectangle_widths, self.rectangle_heights) \
                                      for s,t in rectangle_edges( np.array([c[0] + w/2.0, c[1] + h/2.0]), \
                                                                  np.array([c[0] + w/2.0, c[1] - h/2.0]), \
                                                                  np.array([c[0] - w/2.0, c[1] - h/2.0]), \
                                                                  np.array([c[0] - w/2.0, c[1] + h/2.0]) )]
        
        distances = [np.linalg.norm(p - cp) for cp in closest_points_to_segments]
        idx = np.argmin(distances)
        
        return closest_points_to_segments[idx]
        
class Environment(object):
    def __init__(self, x_range, y_range, obstacles):
        self.obstacles = obstacles.values()
        self.x_range = x_range
        self.y_range = y_range

        w = x_range[1] - x_range[0]
        h = y_range[1] - y_range[0]
        
        self.image = 255*np.ones((h, w, 3), dtype='uint8')
        for obs in self.obstacles:
            for co, wo, ho in zip(obs.rectangle_centers, obs.rectangle_widths, obs.rectangle_heights):
                r = (h-1) - co[1]
                c = co[0]
                min_row = max(int(r - ho/2.0), 0)
                max_row = min(int(r + ho/2.0), h-1)
                
                min_col = max(int(c - wo/2.0), 0)
                max_col = min(int(c + wo/2.0), w-1)
                
                self.image[min_row:max_row, min_col:max_col, :] = (204, 153, 102) 

        
    def point_distance_from_obstacles(self, x, y):
        dist = [obs.distance_to_point(x, y) for obs in self.obstacles]
        return min(dist)
    
    def point_is_in_free_space(self, x, y, epsilon=0.25):
        return self.point_distance_from_obstacles(x,y) > epsilon

    def range_and_bearing_to_closest_obstacle(self, x,y):
        dist = [(self.obstacles[i].distance_to_point(x, y), i) for i in xrange(len(self.obstacles))]
        distance_to_closest_obstacle, idx_closest = min(dist)
        closest_obstacle = self.obstacles[idx_closest]
        cp = closest_obstacle.closest_point_to(np.array([x,y]))
        bearing_to_closest_obstacle = atan2(cp[1]-y, cp[0]-x)
        return distance_to_closest_obstacle, bearing_to_closest_obstacle
        
    def segment_is_in_free_space(self, x1,y1, x2,y2, epsilon=0.5):
        
        if not (self.point_is_in_free_space(x1, y1, epsilon/2.0) and self.point_is_in_free_space(x2, y2, epsilon/2.0)):
            return False
        
        a = np.array([x1, y1])
        b = np.array([x2, y2])

        return not any([segments_intersect(a, b, s, t) for obs in self.obstacles \
                        for c,w,h in zip(obs.rectangle_centers, obs.rectangle_widths, obs.rectangle_heights) \
                        for s,t in rectangle_edges( np.array([c[0] + (w + epsilon)/2.0, c[1] + (h + epsilon)/2.0]), \
                                                    np.array([c[0] + (w + epsilon)/2.0, c[1] - (h + epsilon)/2.0]), \
                                                    np.array([c[0] - (w + epsilon)/2.0, c[1] - (h + epsilon)/2.0]), \
                                                    np.array([c[0] - (w + epsilon)/2.0, c[1] + (h + epsilon)/2.0]) ) ])


    def segment_distance_from_obstacles(self, x1, y1, x2, y2):

        if not self.segment_is_in_free_space(x1, y1, x2, y2, epsilon=1e-10):
            return 0.0

        a = np.array([x1, y1])
        b = np.array([x2, y2])
        
        dist = [point_to_segment_distance(p, a, b) for obs in self.obstacles \
                for c,w,h in zip(obs.rectangle_centers, obs.rectangle_widths, obs.rectangle_heights) for p in rectangle_vertices(c,w,h)]

        return min(dist)


    def raytrace(self, p, theta, max_range, n_evals=50):
        """TODO: implement a less naive collision algo than this"""
        ct = cos(theta)
        st = sin(theta)
        direction = np.array([ct, st])
        
        a = p
        b = p + max_range * direction

        if self.segment_is_in_free_space(a[0], a[1], b[0], b[1], epsilon=1e-10):
            return -1.0

        last_free_dist = 0
        for e in xrange(n_evals):
            dist = e/float(n_evals) * max_range
            c = a + dist * direction
            if not self.point_is_in_free_space(c[0], c[1], epsilon=1e-10):
                return last_free_dist

            last_free_dist = dist 

        
    
    def winding_angle(self, path, point):
        wa = 0
        for i in xrange(len(path)-1):
            p = np.array([path[i].x, path[i].y])
            pn = np.array([path[i+1].x, path[i+1].y])
            
            vp = p - point
            vpn = pn - point
            
            vp_norm = sqrt(vp[0]**2 + vp[1]**2)
            vpn_norm = sqrt(vpn[0]**2 + vpn[1]**2)

            assert (vp_norm > 0)
            assert (vpn_norm > 0)

            z = np.cross(vp, vpn)/(vp_norm * vpn_norm)
            z = min(max(z, -1.0), 1.0)
            wa += asin(z)

        return wa
        
    def homology_vector(self, path):
        L = len(self.obstacles)
        h = np.zeros((L, 1) )
        for i in xrange(L):
            h[i, 0] = self.winding_angle(path, self.obstacles[i].representative_point) 
            
        return h.reshape((L,))

    
=======
>>>>>>> test
class EnvironmentGenerator(object):

    def __init__(self, x_range, y_range, width_range, height_range):
        self.x_range = x_range
        self.y_range = y_range
        self.width_range = width_range
        self.height_range = height_range

    def sample_spatial_poisson_process(self, rate):
        xmin, xmax = self.x_range
        ymin, ymax = self.y_range

        dx = xmax - xmin
        dy = ymax - ymin

        N = stats.poisson( rate * dx * dy ).rvs()
        x = stats.uniform.rvs(xmin, dx, ((N, 1)) )
        y = stats.uniform.rvs(ymin, dy, ((N, 1)) )

        centers = np.hstack((x,y))
        return centers

    def sample_axis_aligned_rectangles(self, density):
        wmin, wmax = self.width_range
        hmin, hmax = self.height_range

        dw = wmax - wmin
        dh = hmax - hmin

        centers = self.sample_spatial_poisson_process(rate=density)
        widths = stats.uniform.rvs(wmin, dw, ((centers.shape[0], 1)) )
        heights = stats.uniform.rvs(hmin, dh, ((centers.shape[0], 1)) )

        return centers, widths, heights

    def merge_rectangles_into_obstacles(self, centers, widths, heights, epsilon):
        """Merges rectangles defined by centers, widths, heights. Two rectangles
        with distance < epsilon are considered part of the same object."""

        G = nx.Graph()
        obstacles = {i: Obstacle(centers[i, :], widths[i, 0], heights[i, 0]) for i in range(len(centers))}
        G.add_nodes_from(obstacles.keys())

        for i in obstacles:
            for j in obstacles:
                if i != j and obstacles[i].distance_to_obstacle(obstacles[j]) < epsilon:
                    G.add_edge(i,j)

        merged_obstacles = {}
        conn_components = nx.connected_components(G)
        for cc in conn_components:
            cc = list(cc)
            new_obs = obstacles[cc[0]]
            for i in range(1, len(cc)):
                new_obs.merge(obstacles[cc[i]])

            merged_obstacles[cc[0]] = new_obs

        return merged_obstacles


class EnvironmentCollection(object):

    def __init__(self):
        self.x_range = []
        self.y_range = []
        self.width_range = []
        self.height_range = []
        self.num_environments = 0
        self.map_collection = {}

    def generate_random(self, x_range, y_range, width_range, height_range, density, num_environments):
        self.x_range = x_range
        self.y_range = y_range
        self.width_range = width_range
        self.height_range = height_range
        self.num_environments = num_environments
        self.map_collection = {}

        eg = EnvironmentGenerator(x_range, y_range, width_range, height_range)
        for i in range(self.num_environments):
            print('Sampling environment', i)
            centers, widths, heights = eg.sample_axis_aligned_rectangles(density)
            obstacles = eg.merge_rectangles_into_obstacles(centers, widths, heights, epsilon=0.2)
            self.map_collection[i] = Environment(self.x_range, self.y_range, obstacles)

    def read(self, pkl_filename):
        file_object = open(pkl_filename, 'rb')
        self.map_collection = pickle.load(file_object)
        file_object.close()

    def save(self, pkl_filename):
        file_object = open(pkl_filename, 'wb')
        pickle.dump(self.map_collection, file_object)
        file_object.close()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python env_generator.py filename_to_save.pkl")
        sys.exit(0)

    x_range=[0, 640]
    y_range=[0, 480]
    width_range=[10, 30]
    height_range=[10,50]

    density = 0.0003
    num_environments = 10

    ec = EnvironmentCollection()
    ec.generate_random(x_range, y_range, width_range, height_range, density, num_environments)
    ec.save(sys.argv[1])
