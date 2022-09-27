#%%
import matplotlib.pyplot as plt
import numpy
import figureSupportModule as fsm
from figureSupportModule import (
    topDownLabels,
    topDownClusters,
    topDownColorMap,
    getCompactedAnnotationsForTmat_percent,
    decorateTmatWithLegend,
)
import seaborn
from matplotlib.image import imread
import h5py, re
from SOAPify import SOAPclassification
from chorddiagram import ChordDiagram

reT = re.compile("T_([0-9]*)")


def getT(s):
    return int(reT.search(s).group(1))


#%% Loading Data

data = {}
for NPname in ["dh348_3_2_3", "to309_9_4"]:
    data[NPname] = dict()
    classificationFile = f"../topDown/{NPname}TopBottom.hdf5"
    with h5py.File(classificationFile, "r") as distFile:
        ClassG = distFile["Classifications/icotodh"]
        for k in ClassG:
            if NPname in k:
                T = getT(k)
                data[NPname][T] = dict()
                classification = ClassG[k][:]
                clusterized = topDownClusters[classification]
                data[NPname][T]["Class"] = SOAPclassification(
                    [], clusterized, topDownLabels
                )

for NP in data:
    for T in data[NP]:
        fsm.addTmatTD(data[NP][T])
        fsm.addTmatNNTD(data[NP][T])


#%%
def AddTmatsAndChord(axesdict, data, T, zoom=0.01):
    reorder = list(range(10))  # [0, 1, 2, 5, 3, 4, 6, 7, 9, 8]
    mask = data["tmat"] == 0
    seaborn.heatmap(
        data["tmat"],
        linewidths=0.1,
        ax=axesdict[f"tmat{T}"],
        fmt="s",
        annot=None,
        mask=mask,
        square=True,
        cmap="rocket_r",
        vmax=1,
        vmin=0,
        cbar=False,
        xticklabels=False,
        yticklabels=False,
    )
    decorateTmatWithLegend("topDown", reorder, axesdict[f"tmat{T}"], zoom=zoom)
    ChordDiagram(
        data["tmatNN"], colors=topDownColorMap, ax=axesdict[f"chord{T}"], onlyFlux=True
    )


figsize = numpy.array([4, 3]) * 3
fig, axes = fsm.makeLayout6and7(figsize, dpi=300)


for T in [300, 400, 500]:

    AddTmatsAndChord(axes, data["to309_9_4"][T], T)
    # AddTmats(axes, data["dh348_3_2_3"][T], T)


# todo: histo
# %%

[
    "npIdeal",
    "np300",
    "tmat300",
    "chord300",
    "np400",
    "tmat400",
    "chord400",
    "np500",
    "tmat500",
    "chord500",
    "Histo",
]


#%%
