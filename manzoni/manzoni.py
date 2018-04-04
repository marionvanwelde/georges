import numpy as np
from .transfer import transfer
from .kick import kick
from .constants import *
from .aperture import aperture_check


def convert_line(line, to_numpy=True):
    def class_conversion(e):
        if e['CLASS'] in ('RFCAVITY', 'HKICKER'):
            e['CLASS_CODE'] = CLASS_CODES['DRIFT']
        if e['CLASS'] not in CLASS_CODES:
            e['CLASS_CODE'] = CLASS_CODES['NONE']
        else:
            e['CLASS_CODE'] = CLASS_CODES[e['CLASS']]
        return e

    def apertype_conversion(e):
        # Default aperture
        if 'APERTYPE' not in e.index.values:
            e['APERTYPE_CODE'] = APERTYPE_CODE_NONE
            e['APERTURE'] = 0.0
            e['APERTURE_2'] = 0.0
            return e
        # Aperture types
        if e['APERTYPE'] == 'CIRCLE':
            e['APERTYPE_CODE'] = APERTYPE_CODE_CIRCLE
        elif e['APERTYPE'] == 'RECTANGLE':
            e['APERTYPE_CODE'] = APERTYPE_CODE_RECTANGLE
        else:
            e['APERTYPE_CODE'] = APERTYPE_CODE_NONE
            e['APERTURE'] = 0.0
            e['APERTURE_2'] = 0.0
        # Aperture sizes
        if isinstance(e['APERTURE'], str):
            s = e['APERTURE'].strip('[{}]').split(',')
            e['APERTURE'] = float(s[0])
            if len(s) > 1:
                e['APERTURE_2'] = float(s[1])
        return e
    # Create or copy missing columns
    if 'CLASS' not in line and 'KEYWORD' in line:
        line['CLASS'] = line['KEYWORD']
    for i in INDEX.keys():
        if i not in line:
            line[i] = 0.0
    # Perform the conversion
    line = line.apply(class_conversion, axis=1)
    line = line.apply(apertype_conversion, axis=1)
    # Adjustments for the final format
    line = line.fillna(0.0)
    if to_numpy:
        return line[list(INDEX.keys())].as_matrix()
    else:
        return line[list(INDEX.keys())]


def transform_variables(line, variables):
    ll = line.reset_index()

    def transform(v):
        i = ll[ll['index'] == v[0]].index.values[0]
        j = INDEX[v[1]]
        return [i, j]
    return list(map(transform, variables))


def adjust_line(line, variables, parameters):
    for i, p in enumerate(parameters):
        line[variables[i][0], variables[i][1]] = p
    return line  # Check later if calling this function will create a copy


def track(line, beam, turns=1, observer=None, **kwargs):
    """
    Tracking through a beamline.
    Code optimized for performance.
    :param line: beamline description in Manzoni format
    :param beam: initial beam
    :param turns: number of tracking turns
    :param observer: Observer object to witness and record the tracking data
    :param kwargs: optional parameters
    :return: Observer.track_end() return value
    """
    # Initial call to the observer
    if observer is not None:
        observer.track_start(beam)
    # Main loop
    for j in range(0, turns):
        for i in range(0, line.shape[0]):
            if line[i, INDEX_CLASS_CODE] in CLASS_CODE_KICK and beam.shape[0] > 0:
                # In place operation
                kick[int(line[i, INDEX_CLASS_CODE])](line[i], beam, **kwargs)
            elif line[i, INDEX_CLASS_CODE] in CLASS_CODE_MATRIX:
                matrices = transfer[int(line[i, INDEX_CLASS_CODE])]
                # For performance considerations, see
                # https://stackoverflow.com/q/48474274/420892
                # b = np.einsum('ij,kj->ik', b, matrix(line[i]))
                beam = beam.dot(matrices(line[i]).T)
            beam = aperture_check(beam, line[i])
            if observer is not None and observer.element_by_element_is_active is True:
                observer.element_by_element(j, i, beam)
        if observer is not None and observer.turn_by_turn_is_active is True:
            observer.turn_by_turn(j, i, beam)
    # Final call to the observer
    if observer is not None:
        return observer.track_end(j, i, beam)
    return