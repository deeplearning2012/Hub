from typing import Tuple
import collections.abc as abc

import numpy as np

import hub.aerial.storage_tensor as storage_tensor

StorageTensor = storage_tensor.StorageTensor

Shape = Tuple[int, ...]


class DynamicTensor:
    def __init__(
        self,
        url: str,
        shape: Shape = None,
        max_shape: Shape = None,
        dtype="float64",
        token=None,
        memcache=None,
    ):
        self._storage_tensor = StorageTensor(
            url, max_shape, dtype=dtype, creds=token, memcache=memcache
        )
        self._dynamic_dims = get_dynamic_dims(shape)
        if max_shape is None:
            self._dynamic_tensor = StorageTensor(url, creds=token, memcache=memcache)
        else:
            if len(self._dynamic_dims) > 0:
                self._dynamic_tensor = StorageTensor(
                    url,
                    shape=(max_shape[0], len(self._dynamic_dims)),
                    dtype="int32",
                    creds=token,
                    memcache=20,
                )
            else:
                self._dynamic_tensor = None
        self.shape = shape
        self.max_shape = max_shape
        assert len(self.shape) == len(self.max_shape)
        for item in self.max_shape:
            assert item is not None
        for item in zip(self.shape, self.max_shape):
            if item[0] is not None:
                assert item[0] == item[1]

    def __getitem__(self, slice_):
        if not isinstance(slice_, abc.Iterable):
            slice_ = [slice_]
        slice_ = list(slice_)
        if self._dynamic_tensor:
            real_shapes = self._dynamic_tensor[slice_[0]]
        else:
            real_shapes = None
        slice_ += [slice(0, None, 1) for i in self.max_shape[len(slice_) :]]
        if real_shapes is not None:
            for r, i in enumerate(self._dynamic_dims):
                if isinstance(slice_[i], int) and slice_[i] < 0:
                    slice_[i] += real_shapes[i]
                elif isinstance(slice_[i], slice) and (
                    slice_[i].stop is None or slice_[i].stop < 0
                ):
                    slice_[i] = slice_stop_changed(
                        slice_[i], (slice_[i].stop or 0) + real_shapes[r]
                    )
        slice_ = tuple(slice_)
        return self._storage_tensor[slice_]

    def __setitem__(self, slice_, value):
        if not isinstance(slice_, abc.Iterable):
            slice_ = [slice_]
        slice_ = list(slice_)
        real_shapes = self._dynamic_tensor[slice_[0]] if self._dynamic_tensor else None
        if real_shapes is not None:
            for r, i in enumerate(self._dynamic_dims):
                if i >= len(slice_):
                    real_shapes[r] = value.shape[i - len(slice_)]
        slice_ += [slice(0, None, 1) for i in self.max_shape[len(slice_) :]]
        if real_shapes is not None:
            for r, i in enumerate(self._dynamic_dims):
                if isinstance(slice_[i], int) and slice_[i] < 0:
                    slice_[i] += real_shapes[i]
                elif isinstance(slice_[i], slice) and (
                    slice_[i].stop is None or slice_[i].stop < 0
                ):
                    slice_[i] = slice_stop_changed(
                        slice_[i], (slice_[i].stop or 0) + real_shapes[r]
                    )
        slice_ = tuple(slice_)
        self._storage_tensor[slice_] = value
        if real_shapes is not None:
            self._dynamic_tensor[slice_[0]] = real_shapes


def get_dynamic_dims(shape):
    return [i for i, s in enumerate(shape) if s is None]


def slice_stop_changed(slice_, new_stop):
    return slice(slice_.start, new_stop, slice_.step)