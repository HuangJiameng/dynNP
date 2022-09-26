#%%
from h5py import File
from HDF5er import saveXYZfromTrajGroup, MDA2HDF5
import numpy
from MDAnalysis import Universe as mdaUniverse
from SOAPify import (
    saponifyGroup,
    createReferencesFromTrajectory,
    getReferencesFromDataset,
    mergeReferences,
    SOAPdistanceNormalized,
    saveReferences,
    SOAPReferences,
)
from dataclasses import dataclass
import scipy.cluster.hierarchy as sch

#%%
FramesRequest = dict(
    ico923_6={
        "v_5f_ih": (0, 566),
        "e_(111)_ih": (0, 830),
        "e_(111)_vih": (0, 828),
        "s_(111)_ih": (0, 892),
        "s_(111)_eih": (0, 893),
        "ss_5f_ih": (0, 312),
        "ss_FCC_ih": (0, 524),
        "ss_HCP_ih": (0, 431),
        "b_5f_ih": (0, 1),
        "b_HCP_ih": (0, 45),
        "b_FCC_ih": (0, 127),
        "b_c_ih": (0, 0),
    },
    to807_11_3={
        "e_(111)_to": (0, 723),
    },
    to976_12_4={
        "v_to": (0, 974),
        "e_(001)_to": (0, 970),
        "e_(001)_vto": (0, 972),
        "e_(111)_vto": (0, 924),
        "s_(001)_to": (0, 950),
        "s_(001)_eto": (0, 940),
        "s_(111)_to": (0, 676),
        "s_(111)_eto": (0, 920),
        "ss_v_to": (0, 611),
        "ss_(001)_to": (0, 258),
        "ss_(111)_to": (0, 278),
        "b_FCC_to": (0, 57),
    },
    dh1086_7_1_3={
        "v_5f_dh": (0, 10),
        "v_slim": (0, 1071),
        "e_(111)_vdh": (0, 50),
        "e_(111)_cdh": (0, 798),
        "e_(111)_dh": (0, 536),
        "e_slim": (0, 1068),
        "e_slim_nv": (0, 1070),
        "s_(111)_slim": (0, 1011),
        "v_(111)_con": (0, 925),
        "s_(111)_dh": (0, 670),
        "ss_HCP_dh": (0, 360),
        "ss_FCC_dh": (0, 669),
        "ss_FCC_con": (0, 921),
        "ss_HCP_con": (0, 797),
        "b_FCC_dh": (0, 399),
        "b_HCP_dh": (0, 154),
        "b_5f_dh": (0, 4),
        "v_con": (0, 924),
        "ev_con": (0, 1024),
    },
    dh1734_5_4_4={
        "e_con": (0, 1130),
        "e_con_v": (0, 1132),
        "s_(001)_dh": (0, 1643),
    },
)

desiredReferenceOrder = [
    # ico
    "v_5f_ih",
    "e_(111)_ih",
    "e_(111)_vih",
    "s_(111)_ih",
    "s_(111)_eih",
    "ss_5f_ih",
    "ss_FCC_ih",
    "ss_HCP_ih",
    "b_5f_ih",
    "b_HCP_ih",
    "b_FCC_ih",
    "b_c_ih",
    # to
    "v_to",
    "e_(001)_to",
    "e_(001)_vto",
    "e_(111)_to",
    "e_(111)_vto",
    "s_(001)_to",
    "s_(001)_eto",
    "s_(111)_to",
    "s_(111)_eto",
    "ss_v_to",
    "ss_(001)_to",
    "ss_(111)_to",
    "b_FCC_to",
    # dh
    "v_5f_dh",
    "v_slim",
    "e_(111)_vdh",
    "e_(111)_cdh",
    "e_(111)_dh",
    "e_slim",
    "e_slim_nv",
    "s_(111)_slim",
    "v_(111)_con",
    "e_con",
    "e_con_v",
    "v_con",
    "ev_con",
    "s_(111)_dh",
    "s_(001)_dh",
    "ss_HCP_dh",
    "ss_FCC_dh",
    "ss_FCC_con",
    "ss_HCP_con",
    "b_FCC_dh",
    "b_HCP_dh",
    "b_5f_dh",
]


@dataclass
class Names:
    cat: str  # :: category
    sub: str = ""  # :: category subscript
    sup: str = " "  # :: category superscript

    def __call__(self) -> str:
        toret = "{" + self.cat + "}"
        if self.sub != "":
            toret += "_{\!_{" + self.sub + "}}"
        if self.sup != "":
            toret += "^{" + self.sup + "}"
        return f"${toret}$"


def nameFromLabel(s):
    id1 = s.index("_")
    id2 = -1 if s.count("_") == 1 else s.index("_", id1 + 1)
    cat = s[:id1]
    sub = s[id1 + 1 : id2]
    sup = " " if id2 == -1 else s[id2 + 1 :]
    return Names(cat, sub, sup)


renames = {k: nameFromLabel(k) for k in desiredReferenceOrder}


def prepareReferenceFrames(FramesRequest, fileName="referenceFrames.hdf5"):
    for NPID in FramesRequest:
        fname = f"{NPID}_minimized.data"
        u = mdaUniverse(fname, atom_style="id type x y z")
        u.atoms.types = ["Au"] * len(u.atoms)
        MDA2HDF5(u, fileName, f"{NPID}", trajChunkSize=1000)

    with File(fileName, "a") as workFile:
        saponifyGroup(
            trajContainers=workFile["Trajectories"],
            SOAPoutContainers=workFile.require_group("SOAP"),
            SOAPOutputChunkDim=1000,
            SOAPnJobs=32,
            SOAPrcut=4.48023312,
            SOAPnmax=8,
            SOAPlmax=8,
        )


def referenceDendroMaker(reference, orientation="left"):
    ndataset = len(reference)
    print(ndataset)
    wholeDistances = numpy.zeros((int(ndataset * (ndataset - 1) / 2)))
    cpos = 0
    for i in range(ndataset):
        for j in range(i + 1, ndataset):
            wholeDistances[cpos] = SOAPdistanceNormalized(
                reference.spectra[i], reference.spectra[j]
            )
            cpos += 1
    sch.dendrogram(
        sch.linkage(wholeDistances, method="complete"),
        labels=reference.names,
        orientation=orientation,
    )


#%%

references = dict()

with File("referenceFrames.hdf5", "r") as workFile:
    for k in FramesRequest:
        references[k] = createReferencesFromTrajectory(
            workFile[f"SOAP/{k}"], FramesRequest[k], 8, 8
        )
# temporary

dhRefs = mergeReferences(*[references[k] for k in references if "dh" in k])
referenceDendroMaker(dhRefs)
# referenceDendroMaker(mergeReferences(*[references[k] for k in references]), "top")
#%%
with File("References.hdf5", "w") as refFile:
    g = refFile.require_group("NPReferences")
    for k in references:
        saveReferences(g, k, references[k])
#%%

myreferences = dict()

with File("References.hdf5", "r") as refFile:
    g = refFile["NPReferences"]
    for k in g:
        myreferences[k] = getReferencesFromDataset(g[k])

allRefs = mergeReferences(*[myreferences[k] for k in myreferences])
#%% reoredering references


idx = numpy.zeros((len(allRefs.names)), dtype=int)
for i, k in enumerate(desiredReferenceOrder):
    idx[i] = allRefs.names.index(k)

reorderedReferences = SOAPReferences(
    names=desiredReferenceOrder,
    spectra=allRefs.spectra[idx],
    lmax=allRefs.lmax,
    nmax=allRefs.nmax,
)


#%%
icoRefs = mergeReferences(*[myreferences[k] for k in myreferences if "ico" in k])  # OK!
toRefs = mergeReferences(*[myreferences[k] for k in myreferences if "to" in k])  # OK!
dhRefs = mergeReferences(*[myreferences[k] for k in myreferences if "dh" in k])


referenceDendroMaker(dhRefs)

#%%
