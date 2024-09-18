# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/42_tabular.model.ipynb.

# %% ../../nbs/42_tabular.model.ipynb 1
from __future__ import annotations
from ..torch_basics import *
from .core import *

# %% auto 0
__all__ = ['emb_sz_rule', 'get_emb_sz', 'TabularModel', 'tabular_config']

# %% ../../nbs/42_tabular.model.ipynb 6
def emb_sz_rule(
    n_cat:int # Cardinality of a category
) -> int:
    "Rule of thumb to pick embedding size corresponding to `n_cat`"
    return min(600, round(1.6 * n_cat**0.56))

# %% ../../nbs/42_tabular.model.ipynb 7
def _one_emb_sz(classes, n, sz_dict=None):
    "Pick an embedding size for `n` depending on `classes` if not given in `sz_dict`."
    sz_dict = ifnone(sz_dict, {})
    n_cat = len(classes[n])
    sz = sz_dict.get(n, int(emb_sz_rule(n_cat)))  # rule of thumb
    return n_cat,sz

# %% ../../nbs/42_tabular.model.ipynb 9
def get_emb_sz(
    to:Tabular|TabularPandas, 
    sz_dict:dict=None # Dictionary of {'class_name' : size, ...} to override default `emb_sz_rule` 
) -> list: # List of embedding sizes for each category
    "Get embedding size for each cat_name in `Tabular` or `TabularPandas`, or populate embedding size manually using sz_dict"
    return [_one_emb_sz(to.classes, n, sz_dict) for n in to.cat_names]

# %% ../../nbs/42_tabular.model.ipynb 10
class TabularModel(Module):
    "Basic model for tabular data."
    def __init__(self, 
        emb_szs:list, # Sequence of (num_embeddings, embedding_dim) for each categorical variable
        n_cont:int, # Number of continuous variables
        out_sz:int, # Number of outputs for final `LinBnDrop` layer
        layers:list, # Sequence of ints used to specify the input and output size of each `LinBnDrop` layer
        ps:float|MutableSequence=None, # Sequence of dropout probabilities for `LinBnDrop`
        embed_p:float=0., # Dropout probability for `Embedding` layer
        y_range=None, # Low and high for `SigmoidRange` activation 
        use_bn:bool=True, # Use `BatchNorm1d` in `LinBnDrop` layers
        bn_final:bool=False, # Use `BatchNorm1d` on final layer
        bn_cont:bool=True, # Use `BatchNorm1d` on continuous variables
        act_cls=nn.ReLU(inplace=True), # Activation type for `LinBnDrop` layers
        lin_first:bool=True, # Linear layer is first or last in `LinBnDrop` layers
        vec_sizes:list=[],
    ):
        ps = ifnone(ps, [0]*len(layers))
        if not is_listy(ps): ps = [ps]*len(layers)
        self.embeds = nn.ModuleList([Embedding(ni, nf) for ni,nf in emb_szs])
        self.emb_drop = nn.Dropout(embed_p)
        self.bn_cont = nn.BatchNorm1d(n_cont) if bn_cont else None
        if vec_sizes:
            self.vec_layers = nn.ModuleList([nn.Sequential(nn.Linear(size, 1), nn.ReLU()) for size in vec_sizes])
        n_emb = sum(e.embedding_dim for e in self.embeds)
        n_vec = len(vec_sizes)
        self.n_emb,self.n_cont = n_emb,n_cont
        sizes = [n_emb + n_cont + n_vec] + layers + [out_sz]
        actns = [act_cls for _ in range(len(sizes)-2)] + [None]
        _layers = [LinBnDrop(sizes[i], sizes[i+1], bn=use_bn and (i!=len(actns)-1 or bn_final), p=p, act=a, lin_first=lin_first)
                       for i,(p,a) in enumerate(zip(ps+[0.],actns))]
        if y_range is not None: _layers.append(SigmoidRange(*y_range))
        self.layers = nn.Sequential(*_layers)

    def forward(self, x_cat, x_cont=None, x_vec=None):
        if self.n_emb != 0:
            x = [e(x_cat[:,i]) for i,e in enumerate(self.embeds)]
            x = torch.cat(x, 1)
            x = self.emb_drop(x)
        if self.n_cont != 0:
            if self.bn_cont is not None: x_cont = self.bn_cont(x_cont)
            x = torch.cat([x, x_cont], 1) if self.n_emb != 0 else x_cont
        if x_vec is not None:
            x_vec = [lin_layer(x_vec[i]) for i,lin_layer in enumerate(self.vec_layers)]
            x_vec = torch.cat(x_vec, 1)
            x_vec = self.emb_drop(x_vec)
            x = torch.cat([x, x_vec], 1) if self.n_emb != 0 or self.n_cont != 0 else x_vec
        return self.layers(x)

# %% ../../nbs/42_tabular.model.ipynb 13
@delegates(TabularModel.__init__)
def tabular_config(**kwargs):
    "Convenience function to easily create a config for `TabularModel`"
    return kwargs
