import numpy as np
P=np.array([-0.3323,0.5071,0.657,-0.6156,-0.0148,0.0799])
def E(wp,my,op):
    w=np.clip(np.asarray(wp,float),.02,.98); L=np.log(w/(1-w)); a=np.log(np.asarray(my,float)+5); b=np.log(np.asarray(op,float)+5)
    z=P[0]+P[1]*L+P[2]*a+P[3]*b+P[4]*L*a+P[5]*L*b; return 1/(1+np.exp(-z))
