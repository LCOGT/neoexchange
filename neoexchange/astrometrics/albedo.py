#the goal of this code it to determind albedo and the diameter based on the albedo

import numpy as np
import matplotlib.pyplot as plt
from astropy.modeling import models, fitting 
import random
import math

#this will generate the x-axis number

x = random.random()
y = random.random()
    
f = 0.253
bright = 0.0168
dark = 0.03  
    
if x < f:
    t = dark

else:
    t = bright

#this is the x and y numbers to be plot. the equation was two fractions so I typed out the numerators to make things easier later and the inside of the sqrt
inside = -2 * math.log(1 - y) 
print inside, y

a = t * math.sqrt(inside)
top1 = a * math.exp(-a ** 2 / 2 * dark ** 2)
top2 = a * math.exp(-a ** 2 / 2 * bright **2)
prr = f * (top1 / dark ** 2) + (1 - f) * (top2 / bright ** 2)

#this should plot the points 
plt.figure(figsize=(8,7))
plt.plot(a, prr, 'ko')
plt.xlabel('Pv')
plt.ylabel('P(Pv)')

plt.show()





