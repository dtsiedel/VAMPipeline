import pickle
import vedo
import vedo.applications

with open('recon.pickle', 'rb') as handle:
    opt_recon = pickle.load(handle)

with open('sino.pickle', 'rb') as handle:
    opt_sino = pickle.load(handle)

vol = vedo.Volume(opt_recon.array)
vedo.applications.RayCastPlotter(vol,bg='black').show(viewup="x")
