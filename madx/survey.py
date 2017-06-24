import os
import pandas as pd
from .. import beamline
from .madx import Madx

MADX_SURVEY_HEADERS_SKIP_ROWS = 6
MADX_SURVEY_DATA_SKIP_ROWS = 8


class SurveyException(Exception):
    """Exception raised for errors in the Survey module."""

    def __init__(self, m):
        self.message = m


def read_survey(file):
    """Read a MAD-X survey file to a datraframe"""
    headers = pd.read_csv(file, skiprows=MADX_SURVEY_HEADERS_SKIP_ROWS, nrows=0, delim_whitespace=True)
    headers.drop(headers.columns[[0,1]], inplace=True, axis=1)
    df = pd.read_csv(file,
                     header = None,
                     names = headers,
                     na_filter = False,
                     delim_whitespace = True,
                     skiprows = MADX_SURVEY_DATA_SKIP_ROWS
                     )
    return df


def survey(**kwargs):
    """Compute the survey of the beamline."""
    # Process arguments
    line = kwargs.get('line', None)
    context = kwargs.get('context', {})
    m = Madx()
    if line is None or m is None:
        raise SurveyException("Beamline and MAD-X objects need to be defined.")

    # Attach the new beamline to MAD-X if needed
    if line not in m.beamlines:
        m.attach(line)
    m.beam(line.name)
    m.survey()
    errors = m.run(context).fatals
    if len(errors) > 0:
        print(m.input)
        print(errors)
        raise SurveyException("MAD-X ended with fatal error.")
    madx_survey = read_survey(os.path.join("/Users/chernals", 'survey.out'))
    line_with_survey = madx_survey.merge(line.line,
                                         left_index=True,
                                         right_index=True,
                                         how='outer',
                                         suffixes=('_SURVEY', '')
                                         ).sort_values(by='S')
    return beamline.Beamline(line_with_survey)
