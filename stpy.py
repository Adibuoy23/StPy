__author__ = 'bramzandbelt'

# Import packages
from psychopy import visual, monitors, core, event, iohub, info, gui
from psychopy.hardware.emulator import launchScan
print 'psychopy version: %s' % info.psychopyVersion
import os
import time
import random # for setting random number generator seed
import calendar
from itertools import chain, compress

import numpy as np
print 'numpy version: %s' % np.__version__
import pandas as pd
print 'pandas version: %s' % pd.__version__
from pandas import DataFrame
# This is to enable printing of all data frame columns
pd.set_option('display.max_columns', None)

import serial

from pprint import pprint
import re

# To Do:
#
# ADD PAUSE KEY FUNCTIONALITY
# =============================================================================
# if pauseKey.keys:
#   td = win._toDraw
#   win._toDraw = []  # hides whatever was being auto-drawn
#   txt = visual.TextStim(win,text='(paused, p to continue)')
#   while not event.getKeys(keyList=['p']):
#     txt.draw()
#     win.flip()
#   win._toDraw = td  # restore auto-draw
#   pauseKey.status = NOT_STARTED
#   pauseKey.keys = []

# Some general stuff
# =============================================================================

# Do not monitor for key presses during wait periods
core.checkPygletDuringWait = False

def check_df_from_csv_file(df):
    """
    <SUMMARY LINE>

    <EXTENDED DESCRIPTION>

    Parameters
    ----------
    <NAME> : <TYPE>
        <DESCRIPTION>

    Returns
    -------
    <NAME> : <TYPE>
        <DESCRIPTION>

    Raises
    ------
    <EXCEPTIONS>

    Usage
    -----
    <USAGE>

    Example
    -------
    <EXAMPLE THAT CAN IDEALLY BE COPY PASTED>
    """

    # Index (*Ix) and keycount (keycount*) columns should be of type object
    # This is to guarantee that NA and integers can be represented. Floats would
    # cause problems.

    # cols = [col for col in df.select_dtypes(exclude = ['int'])
    #           if col.endswith('Ix') or col.startswith('keyCount')]
    # for col in cols:
    #     df[col] = df[col].astype('object')


    # if os.path.isfile(trialListFile):
    #     trialList = pd.read_csv(trialListFile)
    #     ixCols = [col for col in trialList if re.search('Ix$',col)]
    #
    #
    #     # Assertions
    #     # ---------------------------------------------------------------------
    #     for col in ixCols:
    #         assert trialList[col].dtype == np.int or \
    #                all(trialList['cueIx'].isnull()), \
    #             'column {} in file {} contains data other than integers'.format(col,trialListFile)
    #
    #
    #
    #     config['practice']['trialList'] = trialList

    return df
def collect_response(rd,kb, *args, **kwargs):
    """
    Collect responses from response device and keyboard

    This function is called at two stages in the experiment:
    1. Instruction
        Returns count of response keys, escape keys, and other keys to monitor
    2. Experiment
        Updates the log variable with key count and key time information

    Parameters
    ----------
    rd          : dict
                specifies response device properties

    kb          : dict
                specifies keyboard properties

    log         : pandas.core.frame.DataFrame
                trial log

    otherKeys   : list (optional)
                specifies which other keys (from response device or keyboard)
                to monitor

    Returns
    -------
    log         : pandas.core.frame.DataFrame (optional)
                trial log; collect_responses fills in values for keyCount and
                keyTime variables.

    Usage
    -----
    # For collecting experimental data
    log = collect_response(rd,kb,log)

    # For instruction screens
    keyCount = collect_response(rd,kb)

    """
    triggered = None
    otherKeysPressed = None
    otherKeys = None
    log = None

    if len(args) == 0:
        if kwargs:
            if 'log' in kwargs:
                log = kwargs.get('log')
            if 'otherKeys' in kwargs:
                otherKeys = kwargs.get('otherKeys')
    elif len(args) == 1:
        otherKeys = args[0]
    elif len(args) == 2:
        otherKeys = args[0]
        log = args[1]
    elif len(args) > 2:
        # TODO: Add error message
        pass

    # Process inputs
    # -------------------------------------------------------------------------
    rspKeys     = [item
                   for sublist in rd['settings']['rspKeys']
                   for item in sublist]
    keyKey      = rd['settings']['keyKey']
    timeKey     = rd['settings']['timeKey']
    rdClass     = rd['settings']['class']
    escKeys     = kb['settings']['escKeys']

    # Define dynamic variables
    # -------------------------------------------------------------------------
    keyCount    = {key: 0 for key in rspKeys}
    keyTime     = {key: [] for key in rspKeys}

    # Determine response identity and response
    # -------------------------------------------------------------------------
    rdEvents = rd['client'].getEvents()

    for ev in rdEvents:

        evKeys = ev._asdict()[keyKey]
        evTime = ev._asdict()[timeKey]

        print 'Key pressed: %s at time %f' % (evKeys, evTime)

        # If response device is keyboard and escape keys are in event data
        if rdClass == 'Keyboard':

            if any([re.findall(key,ev._asdict()['key']) for key in escKeys]):
                print('Warning: Escape key pressed - Experiment is terminated')
                core.quit()
            if otherKeys:
                if any([re.findall(key,ev._asdict()['key']) for key in otherKeys]):
                    otherKeysPressed = ev._asdict()['key']
                    print otherKeysPressed
                    return keyCount, otherKeysPressed

        # If any of the event keys are in event data
        if any([re.findall(key,evKeys) for key in rspKeys]):
            for key in rspKeys:
                keyCount[key] += evKeys.count(key)
                if isinstance(log,pd.DataFrame):
                    keyTime[key].extend([evTime - log.iloc[0]['trialOns']] * evKeys.count(key))

    # Check if any escape or other keys have been pressed
    # -------------------------------------------------------------------------
    if rdClass != 'Keyboard':

        for ev in kb['client'].getEvents():
            if any([re.findall(key,ev._asdict()['key']) for key in escKeys]):
                print('Warning: Escape key pressed - Experiment is terminated')
                core.quit()
            if otherKeys:
                if any([re.findall(key,ev._asdict()['key']) for key in otherKeys]):
                    otherKeysPressed = ev._asdict()['key']
                    return keyCount, otherKeysPressed

    # For each key, only response times of first two events are stored
    if isinstance(log,pd.DataFrame):

        for key in rspKeys:
            if keyCount[key] >= 2:

                # In case of multiple keystrokes of the same key, only keep
                # events that follow a previous keystroke > 50 ms. Smaller
                # intervals likely reflect contact bounces
                toKeep = [True]
                toKeep.extend((np.diff(keyTime[key]) > 0.05).tolist())

                # Adjust keyCount and keyTime
                keyCount[key] = toKeep.count(True)
                keyTime[key] = list(compress(keyTime[key],toKeep))

        for key in rspKeys:
            if keyCount[key] > 2:
                keyTime[key] = keyTime[key][0:2]
            elif keyCount[key] < 2:
                keyTime[key].extend([float('NaN')] * (2 - keyCount[key]))

            # Convert to numpy ndarray
            keyTime[key] = np.array(keyTime[key])

        # Log response events
        for key in rspKeys:
            log.iloc[0]['keyCount_'+key] = keyCount[key]
            log.iloc[0]['keyTime1_'+key] = keyTime[key][0]
            log.iloc[0]['keyTime2_'+key] = keyTime[key][1]

        return log

    else:

        return keyCount, otherKeysPressed
def compute_trial_statistics(trialStats,rd,log):
    """
    Computes and writes trial descriptive statistics

    Descriptive statistics categories include response time (rt), response time
    difference (rtDiff), and raw processing time (rpt)

    Parameters
    ----------
    trialStats  : dict
                specifies which of the following descriptive statistics need to
                be computed:

                rt      : bool
                        whether or not to compute statistics related to
                        response time (RT): RT of first and second key press
                        (for each key), as well as mean, min, and max across
                        keys

                rtDiff  : bool
                        whether or not to compute statistics related to
                        response time difference: this is only of interest for
                        situations in which a stimulus is associated with
                        multiple key presses

                rpt     : bool
                        whether or not to compute statistics related to
                        raw processing time (rpt), the time between s2 and RT
                        onset: RPT for first and second key press
                        (for each key), as well as mean, min, and max across
                        keys

    rd          : dict
                specifies response device properties

    log         : pandas.core.frame.DataFrame
                trial log

    Returns
    -------
    log         : pandas.core.frame.DataFrame
                trial log; compute_trial_statistics fills in values based on
                the key-value pairs in trialStats:

                if trialStats['rt']:
                    rt1_*, rt2_*, rt1_mean, rt2_mean, rt1_min, rt2_min,
                    rt1_max, rt2_max
                if trialStats['rtDiff']:
                    rtDiff1_*, rtDiff2_*, rtDiff1_mean, rtDiff2_mean
                if trialStats['rpt']:
                    rpt1_*, rpt2_*, rpt1_mean, rpt2_mean, rpt1_min, rpt2_min,
                    rpt1_max, rpt2_max
    """

    rspKeys = [item for sublist in rd['settings']['rspKeys'] for item in sublist]
    rspKeyPairs = rd['settings']['rspKeys']

    s1Ons = log.iloc[0]['s1Ons']
    s2Ons = log.iloc[0]['s2Ons']

    # Response time
    # -------------------------------------------------------------------------
    # Compute response times relative to primary (go) signal for first (rt1)
    # and  second (rt2) key strokes plus their min (fastest), max (slowest),
    # and mean across keys

    rt1 = {key: np.nan for key in rspKeys}
    rt2 = rt1.copy()

    for key in rspKeys:
        rt1[key] = log.iloc[0]['keyTime1_'+key] - s1Ons
        rt2[key] = log.iloc[0]['keyTime2_'+key] - s1Ons

        if trialStats['rt']:
            log.iloc[0]['rt1_'+key] = rt1[key]
            log.iloc[0]['rt2_'+key] = rt2[key]

    if trialStats['rt']:

        log.iloc[0]['rt1_mean'] = np.nanmean(rt1.values())
        log.iloc[0]['rt2_mean'] = np.nanmean(rt2.values())
        log.iloc[0]['rt1_min'] = np.nanmin(rt1.values())
        log.iloc[0]['rt2_min'] = np.nanmin(rt2.values())
        log.iloc[0]['rt1_max'] = np.nanmax(rt1.values())
        log.iloc[0]['rt2_max'] = np.nanmax(rt2.values())

    # Response time difference
    # -------------------------------------------------------------------------
    if trialStats['rtDiff']:
        for pair in rspKeyPairs:
            pairStr = pair[0] + '-' + pair[1]
            log.iloc[0]['rtDiff1_' + pairStr] = rt1[pair[0]] - rt1[pair[1]]
            log.iloc[0]['rtDiff2_' + pairStr] = rt2[pair[0]] - rt2[pair[1]]

        rtDiff1Cols = [col for col in log.columns if col.startswith('rtDiff1_')]
        rtDiff2Cols = [col for col in log.columns if col.startswith('rtDiff2_')]

        log.iloc[0]['rtDiff1_mean'] = log.iloc[0][rtDiff1Cols].abs().mean()
        log.iloc[0]['rtDiff2_mean'] = log.iloc[0][rtDiff2Cols].abs().mean()

    # Raw processing time
    # -------------------------------------------------------------------------
    # Compute response times relative to secondary signal for first (rt1) and
    # second (rt2) key strokes plus their min (fastest), max (slowest), and
    # mean across keys

    if trialStats['rpt']:
        for key in rspKeys:
            log.iloc[0]['rpt1_' + key] = log.iloc[0]['keyTime1_'+key] - s2Ons
            log.iloc[0]['rpt2_' + key] = log.iloc[0]['keyTime2_'+key] - s2Ons

        rpt1Cols = [col for col in log.columns if col.startswith('rpt1_')]
        rpt2Cols = [col for col in log.columns if col.startswith('rpt2_')]

        log.iloc[0]['rpt1_mean'] = log.iloc[0][rpt1Cols].mean()
        log.iloc[0]['rpt2_mean'] = log.iloc[0][rpt2Cols].mean()
        log.iloc[0]['rpt1_min'] = log.iloc[0][rpt1Cols].min()
        log.iloc[0]['rpt2_min'] = log.iloc[0][rpt2Cols].min()
        log.iloc[0]['rpt1_max'] = log.iloc[0][rpt1Cols].max()
        log.iloc[0]['rpt2_max'] = log.iloc[0][rpt2Cols].max()

    return log
def evaluate_block(config,df,blockId,blockLog,trialOnsNextBlock):
    """
    Evaluate block performance

    Parameters
    ----------
    config              : dict
                        specifies StPy experiment properties

    df                  : pandas.core.frame.DataFrame
                        trial log

    blockId             : str or unicode
                        identifier of the block

    blockLog            : pandas.core.frame.DataFrame
                        block log

    trialOnsNextBlock   : numpy.int64
                        time when next block should start; this is used to
                        determine duration of block feedback

    Returns
    -------
    allCritMet          : bool
                        whether or not all predefined task performance criteria
                        have been met

    """

    # Subfunctions
    def assess_performance(stat,lo,hi):
        """
        Evaluates whether statistic is withing lower and upper bounds

        Parameters
        ----------
        stat    : dict
                statistical value to be evaluated

        lo      : int or float
                lower bound

        hi      : int or float
                upper bound

        Returns
        -------
        critMet : bool
                specifies whether or not criterion is met

        """

        if lo <= stat <= hi:
            critMet = True
        else:
            critMet = False

        return critMet
    def get_bounds(config,stat,ix):
        """
        Get lower and upper bounds for a given statistic

        Parameters
        ----------
        config  : dict
                specifies StPy experiment properties

        stat    : str or unicode
                descriptive statistic name

        ix      : int
                stimulus index (only used if bounds vary across stimulus
                indices)

        Returns
        -------
        lo      : int or float
                lower bound of criterion

        hi      : int or float
                upper bound of criterion

        """

        crit = config['feedback']['block']['features'][stat]['criterion']

        if isinstance(crit[0],list):
            return min(crit[ix]), max(crit[ix])
        else:
            return min(crit), max(crit)
    def get_data(df,statType,trialType,stimType,stimIx):
        """
        Obtain data from DataFrame based on which descriptive statistics are computed

        Parameters
        ----------
        df          : pandas.core.series.DataFrame
                    trial log

        statType    : str or unicode
                    statistic on which feedback is presented

        trialType   : pandas.core.series.Series
                    boolean array acting as selector of trials (rows)

        stimType    : pandas.core.series.Series
                    array of stimulus indices

        stimIx      : int
                    stimulus index

        Returns
        -------
        data        : pandas.core.series.Series
                    data on which descriptive statistic are computed

        """

        bla = {'s1Accuracy':    df.trialCorrect[trialType & (stimType == stimIx)].value_counts(),
               's2Accuracy':    df.trialCorrect[trialType & (stimType == stimIx)].value_counts(),
               's1MeanRt':      df.rt1_mean[trialType & (stimType == ix)],
               's1MeanRtDiff':  df.rtDiff1_mean[trialType & (stimType == ix)]}

        data = bla[statType]

        return data
    def get_desc_stat(data,statType):
        """
        Compute descriptive statistic on data

        Parameters
        ----------
        data        : int or float
                    data on which descriptive statistic is computed

        statType    : str or unicode
                    statistic on which feedback is presented

        Returns
        -------
        descStat    : int or float
                    descriptive statistic

        """

        # Assertions
        knownStatTypes = ['s1Accuracy','s2Accuracy','s1MeanRt','s1MeanRtDiff']
        assert statType in knownStatTypes, 'unknown statType %s' % statType

        if statType == 's1Accuracy' or statType == 's2Accuracy':

            if True in data.index:
                nTrue       = data[True].astype(float)
                nTrial      = data.sum().astype(float)
                pCorrect    = nTrue / nTrial
                descStat    = (pCorrect * 100).round()
            else:
                descStat    = 0

        elif statType == 's1MeanRt':
            if data.empty:
                descStat = np.nan
            else:
                meanRt = data.mean() * 1000
                if np.isnan(meanRt):
                    descStat = np.nan
                else:
                    descStat = meanRt.round()
        elif statType == 's1MeanRtDiff':
            if data.empty:
                descStat = np.nan
            else:
                meanRtDiff = data.abs().mean() * 1000
                if np.isnan(meanRtDiff):
                    descStat = np.nan
                else:
                    descStat = meanRtDiff.round()
        else:
            descStat = np.nan

        return descStat
    def get_feedback_message(config,stat,ix):
        """
        Determine what feedback should be presented

        Parameters
        ----------
        config      : dict
                    specifies StPy experiment properties

        stat        : str or unicode
                    descriptive statistic name

        ix          : int
                    list index

        Returns
        -------
        posMes      : str, unicode, or list
                    feedback message if performance criterion is met

        negMes      : str, unicode, or list
                    feedback message if performance criterion is not met

        """

        posMes = config['feedback']['block']['features'][stat]['feedbackPos']
        negMes = config['feedback']['block']['features'][stat]['feedbackNeg']

        if isinstance(posMes,list):
            if len(posMes) == 1:
                pos = posMes[0]
            elif len(posMes) > 1:
                pos = posMes[ix]
        else:
            pos = posMes

        if isinstance(negMes,list):
            if len(negMes) == 1:
                neg = negMes[0]
            elif len(negMes) > 1:
                neg = negMes[ix]
        else:
            neg = negMes

        return str(pos), str(neg)
    def update_feedback_log(log,stimIx,stat,statType,critMet):
        """
        Update block log

        Logs performance level and whether or not preset performance criterion
        is met.

        Parameters
        ----------
        log         : pandas.core.frame.DataFrame
                    block log

        stimIx      : int
                    stimulus index

        stat        : numpy.float64 or numpy.int
                    performance

        statType    : str or unicode
                    statistic on which feedback is presented

        critMet     : bool
                    whether or not performance criterion is met

        Returns
        -------
        log         : pandas.core.frame.DataFrame
                    block log

        """

        # Dict of formatted strings, referring to columns in log
        strStatCol      = {'s1Accuracy':    's1Acc_%.2d',
                           's2Accuracy':    's2Acc_%.2d',
                           's1MeanRt':      's1MeanRt_%.2d',
                           's1MeanRtDiff':  's1MeanRtDiff_%.2d'}
        strCritCol      = {'s1Accuracy':    's1AccCritMet_%.2d',
                           's2Accuracy':    's2AccCritMet_%.2d',
                           's1MeanRt':      's1MeanRtCritMet_%.2d',
                           's1MeanRtDiff':  's1MeanRtDiffCritMet_%.2d'}

        # Column names for statistic and criterion
        colStat         = strStatCol[statType] % stimIx
        colCrit         = strCritCol[statType] % stimIx

        # Update the log
        log[colStat]    = stat
        log[colCrit]    = critMet

        return log
    def update_feedback_screen(win,feedbackStim,stim,stat,statType,critMet,posMes,negMes):
        """
        Update feedback stimulus

        Parameters
        ----------
        win             : psychopy.visual.window.Window
                        PsychoPy window object, in which stimuli are presented

        feedbackStim    : dict
                        Specifies aspects of the feedback: stimulus identity,
                        performance, and feedback message

        stim            : psychopy.visual.text.TextStim or psychopy.visual.text.ImageStim
                        PsychoPy stimulus to which feedback relates

        stat            : numpy.float64 or numpy.int
                        performance

        statType        : str or unicode
                        statistic on which feedback is presented

        critMet         : bool
                        whether or not performance criterion is met

        posMes          : str or unicode
                        feedback message if performance criterion is met

        negMes          : str or unicode
                        feedback message if performance criterion is not met

        Returns
        -------
        feedbackStim    : dict
                        Specifies aspects of the feedback: stimulus identity,
                        performance, and feedback message

        """

        # Define some variables
        # -----------------------------------------------------------------
        stimName        = stim.name[stim.name.find('_')+1:]

        stimNameText    = get_empty_text_stim(win)
        performText     = get_empty_text_stim(win)
        feedbackText    = get_empty_text_stim(win)

        posFeedbackColor = (255, 255, 255)
        negFeedbackColor = (255, 0, 0)

        # Stimulus
        # -----------------------------------------------------------------
        stimNameText.setText(stimName)
        feedbackStim['stim'].append(stimNameText)

        # Performance
        # -----------------------------------------------------------------

        statStr = {'s1Accuracy':    'accuracy:  %0.f%% correct',
                   's2Accuracy':    'accuracy:  %0.f%% correct',
                   's1MeanRt':      'speed:     %0.f ms',
                   's1MeanRtDiff':  'synchrony: %0.f ms difference'}

        performText.setText(statStr[statType] % stat)

        if critMet:
            performText.setColor(posFeedbackColor,'rgb255')
        else:
            performText.setColor(negFeedbackColor, 'rgb255')

        feedbackStim['performance'].append(performText)

        # Feedback
        # -----------------------------------------------------------------
        if critMet:
            feedbackText.setText(posMes)
            feedbackText.setColor(posFeedbackColor,'rgb255')
        else:
            feedbackText.setText(negMes)
            feedbackText.setColor(negFeedbackColor, 'rgb255')

        feedbackStim['feedback'].append(feedbackText)

        return feedbackStim

    window          = config['window']['window']
    trialStats      = config['statistics']['trial']

    s1              = df.s1Ix
    s2              = df.s2Ix
    s1Trial         = (s1.notnull()) & (s2.isnull())
    s2Trial         = s2.notnull()

    anyS1Trial      = any(s1Trial)
    anyS2Trial      = any(s2Trial)

    trialTypeExist  = {'s1Accuracy':     anyS1Trial,
                       's2Accuracy':     anyS2Trial,
                       's1MeanRt':       anyS1Trial,
                       's1MeanRtDiff':   anyS1Trial}

    trialType       = {'s1Accuracy':     s1Trial,
                       's2Accuracy':     s2Trial,
                       's1MeanRt':       s1Trial,
                       's1MeanRtDiff':   s1Trial}

    # Unique indices of relevant stimulus present in data frame
    uniqueStimIxs   =  {'s1Accuracy':     sorted(s1[s1.notnull()].unique().tolist()),
                        's2Accuracy':     sorted(s2[s2.notnull()].unique().tolist()),
                        's1MeanRt':       sorted(s1[s1.notnull()].unique().tolist()),
                        's1MeanRtDiff':   sorted(s1[s1.notnull()].unique().tolist())}

    # Relevent stimulus type to select on
    stimType        = {'s1Accuracy':    s1,
                       's2Accuracy':     s2,
                       's1MeanRt':       s1,
                       's1MeanRtDiff':   s1}

    # Stimulus
    stimulus        =  {'s1Accuracy':     config['stimuli']['s1'],
                        's2Accuracy':     config['stimuli']['s2'],
                        's1MeanRt':       config['stimuli']['s1'],
                        's1MeanRtDiff':   config['stimuli']['s1']}


    # Task performance features to provide feedback on
    features        = config['feedback']['block']['features']
    feedbackFeat    = [key for key in features.keys() if features[key]['enable'] and trialTypeExist[key]]

    blockFeedback   = config['feedback']['block']['features']
    blockFeedbackStim = {'stim': [],
                         'performance': [],
                         'feedback': []}

    criteriaMet     = []

    for feat in sorted(feedbackFeat):

        for ix in uniqueStimIxs[feat]:

            lowerBound, upperBound  = get_bounds(config=config,
                                                 stat=feat,
                                                 ix=ix)

            posMessage, negMessage  = get_feedback_message(config=config,
                                                           stat=feat,
                                                           ix=ix)

            data = get_data(df=df,
                            statType=feat,
                            trialType=trialType[feat],
                            stimType=stimType[feat],
                            stimIx=ix)

            if not data.empty:

                descStat = get_desc_stat(statType=feat,
                                         data=data)
                thisCritMet = assess_performance(stat=descStat,
                                                 lo=lowerBound,
                                                 hi=upperBound)

                criteriaMet.append(thisCritMet)

                # Update feedback screen
                blockFeedbackStim = update_feedback_screen(win=window,
                                                           feedbackStim=blockFeedbackStim,
                                                           stim=stimulus[feat][ix],
                                                           stat=descStat,
                                                           statType=feat,
                                                           critMet=thisCritMet,
                                                           posMes=posMessage,
                                                           negMes=negMessage)

                # Update feedback log
                blockLog     = update_feedback_log(log=blockLog,
                                                   stimIx=ix,
                                                   stat=descStat,
                                                   statType=feat,
                                                   critMet=thisCritMet)

    allCritMet = all(criteriaMet)

    # Display feedback
    # -------------------------------------------------------------------------

    # Count how lines feedback
    nLines = len(blockFeedbackStim['stim'])

    # Feedback title, containing block ID
    blockTitleStim = get_empty_text_stim(window)
    yPos = (float(nLines) - 1)/2 + 2
    xPos = 0
    blockTitleStim.setText('Block %s' % (blockId))
    blockTitleStim.setPos((xPos,yPos))
    blockTitleStim.setHeight(1)
    blockTitleStim.alignHoriz = 'center'
    blockTitleStim.setAutoDraw(True)

    # Loop over feedback lines
    for iStim in range(nLines):

            # Set position of the stimulus
            yPos = (float(nLines) - 1)/2 - iStim
            xPos = -12

            blockFeedbackStim['stim'][iStim].setPos((xPos,yPos))
            blockFeedbackStim['stim'][iStim].setHeight(0.75)
            blockFeedbackStim['stim'][iStim].alignHoriz = 'left'
            blockFeedbackStim['stim'][iStim].setAutoDraw(True)

            # Set position of performance stimulus
            xPos = -5
            blockFeedbackStim['performance'][iStim].setPos((xPos,yPos))
            blockFeedbackStim['performance'][iStim].setHeight(0.75)
            blockFeedbackStim['performance'][iStim].alignHoriz = 'left'

            blockFeedbackStim['performance'][iStim].setAutoDraw(True)

            # Set position of feedback stimulus
            xPos = 5
            blockFeedbackStim['feedback'][iStim].setPos((xPos,yPos))
            blockFeedbackStim['feedback'][iStim].setHeight(0.75)
            blockFeedbackStim['feedback'][iStim].alignHoriz = 'left'

            blockFeedbackStim['feedback'][iStim].setAutoDraw(True)

    window.flip()

    tNow                = config['clock'].getTime()
    feedbackDuration    = config['feedback']['block']['duration']

    if trialOnsNextBlock == 0:
        core.wait(feedbackDuration)
    elif tNow + feedbackDuration < trialOnsNextBlock:
        core.wait(feedbackDuration)
    elif tNow < trialOnsNextBlock:
        core.wait(5)
    else:
        core.wait(trialOnsNextBlock - tNow - 2)

    blockTitleStim.setAutoDraw(False)
    for iStim in range(nLines):
        blockFeedbackStim['stim'][iStim].setAutoDraw(False)
        blockFeedbackStim['performance'][iStim].setAutoDraw(False)
        blockFeedbackStim['feedback'][iStim].setAutoDraw(False)
    window.flip()

    return allCritMet
def evaluate_trial(evalData,feedbackDur,window,stimuli,log):
    """
    Evaluate trial performance and present trial feedback

    Parameters
    ----------
    evalData    : dict
                specifies information about how trial should be evaluated,
                this includes:

                evalDataFile    : dict
                                specifies trial evaluation data files for each
                                of the possible response devices
                evalData        : pandas.core.frame.DataFrame
                                all stimulus-response combinations specified
                                in the trial evaluation data file

                correct         : pandas.core.series.Series
                                accuracy for each of the stimulus-response
                                combinations

                responseType    : pandas.core.series.Series
                                response type for each of the stimulus-response
                                combinations

                feedback        : pandas.core.series.Series
                                feedback for each of the stimulus-response
                                combinations

                trialType       : pandas.core.series.Series
                                trial type for each of the stimulus-response
                                combinations

    feedbackDur : float
                trial feedback duration (in seconds)

    window      : psychopy.visual.window.Window
                PsychoPy window object, in which stimuli are presented

    stimuli     : dict
                specifies PsychoPy stimuli, including the feedback and inter-
                trial interval stimulus

    log         : pandas.core.frame.DataFrame
                trial log

    Returns
    -------
    log         : pandas.core.frame.DataFrame
                trial log; evaluate_trial fills in values for the following
                variables: trialCorrect, trialType, responseType, and
                trialFeedback

    """

    # Process inputs
    # =========================================================================

    # Assertions
    # -------------------------------------------------------------------------

    # specific to evalData and log (window and stimulis should have been
    # checked already and not have been updated

    # Define dynamic variables
    # -------------------------------------------------------------------------
    trialCorrect    = []
    trialLabel      = []
    trialFeedback   = []

    # Trial evaluation
    # =========================================================================

    ix = log.index.tolist()[0]

    # Match pattern, using stimulus and response data
    source = evalData['evalData'].fillna(float('inf'))
    patternDict= log[source.columns].fillna(float('inf')).to_dict()
    pattern = {key: [value[ix]] for key,value in patternDict.iteritems()}
    iRow = source.isin(pattern).all(1)

    if sum(iRow) == 0:

        trialCorrect = False

        # If no match, try to match using stimulus data only to determine trialType
        sourceStim = evalData['evalData'][['s1Ix','s2Ix']].fillna(float('inf'))
        patternDictStim = log[sourceStim.columns].fillna(float('inf')).to_dict()
        patternStim = {key: [value[ix]] for key,value in patternDictStim.iteritems()}
        iRow = sourceStim.isin(patternStim).all(1)

        uniqueTrialTypes = evalData['trialType'].loc[iRow].unique()
        if len(uniqueTrialTypes) == 0:
            trialType = 'NOC' # Not otherwise classified
        elif len(uniqueTrialTypes) == 1:
            trialType = uniqueTrialTypes.tolist()[0]
        else:
            trialType = "Non-unique: %s" % ', '.join(uniqueVals.tolist())

        responseType = 'NOC' # Not otherwise classified
        trialFeedback = 'incorrect'

    elif sum(iRow) == 1:

        trialCorrect    = evalData['correct'].loc[iRow].as_matrix().tolist()[0]
        trialType       = evalData['trialType'].loc[iRow].as_matrix().tolist()[0]
        responseType    = evalData['responseType'].loc[iRow].as_matrix().tolist()[0]
        trialFeedback   = evalData['feedback'].loc[iRow].as_matrix().tolist()[0]

    elif sum(iRow) > 1:

        # Determine if there is one unique trialCorrect value among selected rows
        uniqueTrialCorrect = evalData['correct'].loc[iRow].unique()
        if len(uniqueTrialCorrect) == 0:
            trialCorrect = 'Unknown'
        elif len(uniqueTrialCorrect) == 1:
            trialCorrect = uniqueTrialCorrect.tolist()[0]
        else:
            trialCorrect = "Non-unique: %s" % ', '.join(uniqueTrialCorrect.tolist())

        # Determine if there is one unique trialType among selected rows
        uniqueTrialTypes = evalData['trialType'].loc[iRow].unique()
        if len(uniqueTrialTypes) == 0:
            trialType = 'NOC' # Not otherwise classified
        elif len(uniqueTrialTypes) == 1:
            trialType = uniqueTrialTypes.tolist()[0]
        else:
            trialType = "Non-unique: %s" % ', '.join(uniqueTrialTypes.tolist())

        # Determine if there is one unique response type among selected rows
        uniqueResponseTypes = evalData['responseType'].loc[iRow].unique()
        if len(uniqueResponseTypes) == 0:
            responseType = 'NOC' # Not otherwise classified
        elif len(uniqueResponseTypes) == 1:
            responseType = uniqueResponseTypes.tolist()[0]
        else:
            responseType = "Non-unique: %s" % ', '.join(uniqueResponseTypes.tolist())

        # Determine if there is one unique trial feedback among selected rows
        uniqueTrialFeedback = evalData['feedback'].loc[iRow].unique()
        if len(uniqueTrialFeedback) == 0:
            trialFeedback = 'incorrect' # Not otherwise classified
        elif len(uniqueTrialFeedback) == 1:
            trialFeedback = uniqueTrialFeedback.tolist()[0]
        else:
            trialFeedback = 'incorrect'

        print('Warning: combination of stimuli and response(s) matches multiple criteria.')
        print('--------------------------------------------------------------')
        print('Stimuli and response(s) on this trial:')
        pprint(pattern)
        print('trialCorrect: \t %s' % (trialCorrect))
        print('trialType: \t %s' % (trialType))
        print('responseType: \t %s' % (responseType))
        print('trialFeedback: \t %s' % (trialFeedback))

    log.iloc[0]['trialCorrect']     = trialCorrect
    log.iloc[0]['trialType']        = trialType
    log.iloc[0]['responseType']     = responseType
    log.iloc[0]['trialFeedback']    = trialFeedback

    # SOA adjustments
    # =========================================================================

    # newSoa = []
    #
    # if soa['type'] == 'staircase':
    #
    #     soaIx = []
    #     soa = []
    #
    #
    #     if trialLabel == 'correct':
    #         newSoa = soa + soaStep
    #     else:
    #         newSoa = soa - soaStep

    # Feedback
    # =========================================================================

    stimuli['feedback'][0].setText(trialFeedback)
    stimuli['feedback'][0].setAutoDraw(True)
    stimuli['iti'][0].setAutoDraw(True)
    window.flip()
    core.wait(feedbackDur)
    stimuli['feedback'][0].setAutoDraw(False)
    stimuli['iti'][0].setAutoDraw(True)
    window.flip()
    stimuli['iti'][0].setAutoDraw(False)

    return log
def get_empty_text_stim(window):
    """
    Returns an empty PsychoPy text stimulus object

    This object has the following properties:

    text        = '',
    font        = 'Arial',
    pos         = (0,0),
    color       = [1.0, 1.0, 1.0],
    colorSpace  = 'rgb',
    opacity     = 1.0,
    bold        = False,
    italic      = False,
    alignHoriz  = 'center',
    alignVert   = 'center',
    wrapWidth   = None,
    autoLog     = None


    Parameters
    ----------
    window      : psychopy.visual.window.Window
                PsychoPy window object, in which stimuli are presented

    Returns
    -------
    textStim    : psychopy.visual.TextStim
                PsychoPy text stimulus object

    """
    textStim = visual.TextStim(window,
                        text='',
                        font='Arial',
                        pos=(0,0),
                        color=[1.0, 1.0, 1.0],
                        colorSpace='rgb',
                        opacity=1.0,
                        bold=False,
                        italic=False,
                        alignHoriz='center',
                        alignVert='center',
                        wrapWidth=None,
                        autoLog=None)

    textStim.setSize(2,units='deg')

    return textStim
def define_stimulus(window,stimInfo,*args):
    """
    Make PsychoPy stimuli based on user input

    Currently, only stimuli of type TextStim and ImageStim are supported.

    Parameters
    ----------
    window      : psychopy.visual.window.Window
                PsychoPy window object, in which stimuli are presented

    stimInfo    : dict
                stimulus information specified by user in experiment
                configuration file

    stimType    : str or unicode (optional)
                stimulus type

    Returns
    -------
    stimulus    : dict
                specifies properties of the stimuli

    """

    # Process inputs
    # -------------------------------------------------------------------------

    # TODO: See if assertions require __debug__ variable
    assert type(window) is visual.window.Window, \
        'window is not of class visual.window.Window'
    assert type(stimInfo) is dict, \
        'stimInfo is not of type dict'
    for key in ['type','content','name']:
        assert stimInfo.has_key(key), \
            'stimInfo does not contain key {0:s}'.format(key)

    if len(args) == 1:
        stimType = args[0]
    else:
        stimType = ''

    nStimulus = len(stimInfo['content'])

    # Initialize list of stimuli
    stimulus = [None] * nStimulus

    for i in range(nStimulus):

        stimulus[i] = init_stimulus(window,stimInfo['type'])

        assert (type(stimulus[i]) is
                visual.text.TextStim or
                visual.image.ImageStim), \
                "stimulus is neither a TextStim nor an ImageStim"

        # Set stimulus name
        if isinstance(stimInfo['name'],list):
            stimulus[i].name = ''.join([stimType,'_',stimInfo['name'][i]])
        else:
            stimulus[i].name = ''.join([stimType,'_',stimInfo['name']])

        # Text stimuli
        # ---------------------------------------------------------------------
        if type(stimulus[i]) is visual.text.TextStim:

            # Set stimulus content
            if os.path.isfile(stimInfo['content'][i]):
                with open(stimInfo['content'][i]) as txtFile:
                    stimulus[i].setText(txtFile.read())
            else:
                stimulus[i].setText(stimInfo['content'][i])

            # Set other parameters
            if 'fontFile' in stimInfo:
                if stimInfo['fontFile']:
                    stimulus[i].fontFiles = stimInfo['fontFile']
            if 'font' in stimInfo:
                if stimInfo['font']:
                    stimulus[i].setFont(stimInfo['font'])
            if 'ori' in stimInfo:
                if stimInfo['ori']:
                    stimulus[i].setOri(stimInfo['ori'])
            if 'height' in stimInfo:
                if stimInfo['height']:
                    stimulus[i].setHeight(stimInfo['height'])
            if 'pos' in stimInfo:
                if stimInfo['pos']:
                    stimulus[i].setPos(stimInfo['pos'])
            if 'color' in stimInfo:
                if stimInfo['color']:

                    # Check if color vary or be the same across different stimuli of this type
                    if all([isinstance(stimInfo['color'],list),len(stimInfo['color']) == 3,isinstance(stimInfo['color'][0],int)]):
                        stimulus[i].setColor(stimInfo['color'], 'rgb255')
                    elif all([isinstance(stimInfo['color'],list),len(stimInfo['color']) == len(stimInfo['content']),isinstance(stimInfo['color'][0],list)]):
                        stimulus[i].setColor(stimInfo['color'][i], 'rgb255')

            if 'opacity' in stimInfo:
                if stimInfo['opacity']:
                    stimulus[i].setOpacity(stimInfo['opacity'])

        # Image stimuli
        # ---------------------------------------------------------------------
        elif type(stimulus[i]) is visual.image.ImageStim:

            # Set stimulus content
            stimulus[i].setImage(stimInfo['content'][i])

            # Set other parameters
            if stimInfo['ori']:
                stimulus[i].setOri(stimInfo['ori'])
            if stimInfo['pos']:
                stimulus[i].setPos(stimInfo['pos'])

    return stimulus
def stim_to_frame_mat(config,trial,log):
    """
    <SUMMARY LINE>

    <EXTENDED DESCRIPTION>

    Parameters
    ----------
    config      : dict
                specifies StPy experiment properties

    trial       : pandas.core.series.Series
                boolean array acting as selector of trials (rows)

    log         : pandas.core.frame.DataFrame
                trial log

    Returns
    -------
    log         : pandas.core.frame.DataFrame
                trial log; stim_to_frame_mat fills in stimulus properties,
                including information about onsets, durations

    stim_list   : list
                list of PsychoPy stimuli

    u           : numpy.ndarray
                stimulus-by-frame array specifying for each combination of
                stimulus (row) and frame (column) whether or not the stimulus
                should be displayed

    f_on_off    : numpy.ndarray
                stimulus-by-2 array specifying the frame indices of stimulus
                onset (first column) and stimulus offset (second column)

    trial_dur   : numpy.ndarray
                trial duration (in seconds), based on onsets and durations of
                the fixation, cue, s1, and s2 stimulus.

    """

    trialLogIx = log.index.tolist()[0]

    stimuli = config['stimuli']

    def append_it(trial,log,stim,stim_list,ons,dur):
        """

        Appends stimulus list

        Parameters
        ----------
        trial       : pandas.core.series.Series
                    trial data

        log         : pandas.core.frame.DataFrame
                    trial log

        stim        : str or unicode
                    stimulus name

        stim_list   : list
                    list of stimuli

        ons         : numpy.ndarray
                    array of stimulus onsets

        dur         : numpy.ndarray
                    array of stimulus durations

        Returns
        -------
        stim_list   : list
                    list of stimuli

        newOns      : numpy.ndarray
                    array of stimulus onsets

        newDur      : numpy.ndarray
                    array of stimulus durations

        log         : pandas.core.frame.DataFrame
                    trial log

        """

        if not pd.isnull(trial[stim + 'Ix']):

            # Identify stimulus index
            i = trial.loc[stim + 'Ix'].astype(int)

            # Append stimulus list, onset array, and duration array
            stim_list.append(stimuli[stim][i])
            stimOns    = float(trial[stim + 'Ons'])
            stimDur    = float(trial[stim + 'Dur'])
            newOns     = np.hstack([ons,stimOns])
            newDur     = np.hstack([dur,stimDur])

            log.loc[trialLogIx,[stim + 'Ix']] = i

            # N.B. These are the intended stimulus onsets and durations. They
            # are replace by the actual onsets and durations in present_stimuli
            log.loc[trialLogIx,[stim + 'Ons']] = stimOns
            log.loc[trialLogIx,[stim + 'Dur']] = stimDur

            if stim == 's2':
                log.loc[trialLogIx,['soaIx']] = trial.loc['soaIx'].astype(int)

        else:
            newOns = ons
            newDur = dur

            for col in ['Ix','Ons','OnsDt','Dur','DurDt']:
                log.loc[trialLogIx,[stim + col]] = np.nan

            if stim == 's2':
                log.loc[trialLogIx,['soaIx']]   = np.nan


        return stim_list, newOns, newDur, log

    stim_list    = []
    ons         = np.array([],dtype=int)
    dur         = np.array([],dtype=int)

    stimSet     = set(config['stimuli'].keys())

    for stim in stimSet.intersection(['fix','cue','s1','s2']):
        stim_list, ons, dur, log = append_it(trial=trial,
                                            log=log,
                                            stim=stim,
                                            stim_list=stim_list,
                                            ons=ons,
                                            dur=dur)

    # Append iti stimulus to stim_list
    stim_list.append(stimuli['iti'][0])

    dt = np.array([1./config['window']['frameRate']])
    trial_dur = np.array(np.max(ons + dur))

    # Make stimulus-by-frame matrix (u)
    u, f_on_off, t = time_to_frame(ons=ons, dur=dur, dt=dt, trial_dur=trial_dur)

    return log, stim_list, u, f_on_off, trial_dur
def init_log(config):
    """
    Initializes and saves a pandas DataFrame for logging stop task data and
    returns

    Parameters
    ----------
    config      : dict
                specifies StPy experiment properties

    Returns
    -------
    trialCols   : list
                columns in trial log

    blockCols   : list
                columns in block log

    sessColumns : list
                columns in trial log and block log containing session-specific data

    sessData    : list
                session-specific data


    """


    # Process inputs
    # -------------------------------------------------------------------------


    # Assertions

    ###########################################################################
    # SESSION-SPECIFIC COLUMNS AND DATA
    ###########################################################################

    idColumnsSess   = ['studyId',
                       'taskVersionId',
                       'sessionId',
                       'experimenterId']

    idDataSess      = [config['study']['studyId'],
                       config['study']['taskVersionId'],
                       config['session']['sessionId'],
                       config['session']['experimenterId']]

    techColumnsSess = ['responseDevice',
                       'refreshRate',
                       'rngSeed']

    techDataSess    = [config['apparatus']['rd']['settings']['class'],
                       config['window']['frameRate'],
                       config['session']['rngSeed']]

    ixColumnsSess   = ['subjectIx',
                       'groupIx',
                       'sessionIx']

    ixDataSess      = [config['subject']['subjectIx'],
                       config['subject']['groupIx'],
                       config['session']['sessionIx']]

    timeColumnsSess = ['sessDate',
                       'sessTime']
    timeDataSess    = [config['session']['date'],
                       config['session']['time']]

    sessColumns     = []
    sessColumns     += idColumnsSess
    sessColumns     += techColumnsSess
    sessColumns     += ixColumnsSess
    sessColumns     += timeColumnsSess

    sessData        = []
    sessData        += idDataSess
    sessData        += techDataSess
    sessData        += ixDataSess
    sessData        += timeDataSess

    # # Copy columns to prevent that sessColumns is updated
    # trialColumns    = list(sessColumns)
    # blockColumns    = list(sessColumns)

    ###########################################################################
    # TRIAL-SPECIFIC COLUMNS
    ###########################################################################

    def init_trial_log(config,columns):

        # Identifiers
        # =====================================================================
        idColumns               = ['blockId']

        # Indices
        # =====================================================================
        ixColumns               = ['blockIx',
                                   'trialIx']

        if config['stimConfig']['fix']['content'] is not None:
            ixColumns += ['fixIx']
        if config['stimConfig']['cue']['content'] is not None:
            ixColumns += ['cueIx']
        if config['stimConfig']['s1']['content'] is not None:
            ixColumns += ['s1Ix']
        if config['stimConfig']['s2']['content'] is not None:
            ixColumns += ['s2Ix','soaIx']

        # Time
        # =====================================================================
        timeColumns             = ['tSession',
                                   'tBlock',
                                   'trialOns',
                                   'trialDur']

        if config['stimConfig']['fix']['content'] is not None:
            timeColumns+= ['fixOns','fixOnsDt','fixDur','fixDurDt']
        if config['stimConfig']['cue']['content'] is not None:
            timeColumns += ['cueOns','cueOnsDt','cueDur','cueDurDt']
        if config['stimConfig']['s1']['content'] is not None:
            timeColumns += ['s1Ons','s1OnsDt','s1Dur','s1DurDt']
        if config['stimConfig']['s2']['content'] is not None:
            timeColumns += ['s2Ons','s2OnsDt','s2Dur','s2DurDt']

        # MRI Trigger
        # =====================================================================
        triggerColumns          = ['waitedForTrigger']

        # Feedback
        # =====================================================================
        feedbackColumns         = ['trialCorrect',
                                   'trialType',
                                   'responseType',
                                   'trialFeedback']

        # Response event times
        # =====================================================================
        rspKeys = [item
                   for sublist
                   in config['apparatus']['rd']['settings']['rspKeys']
                   for item in sublist]

        respEvColumns = list(chain.from_iterable(('keyCount_'+key,
                                                  'keyTime1_'+key,
                                                  'keyTime2_'+key)
                                                 for key in rspKeys))

        # Descriptive statistics
        # =====================================================================
        trialStats      = config['statistics']['trial']
        rspKeyPairs    = config['apparatus']['rd']['settings']['rspKeys']
        statsColumns    = []

        if config['statistics']['trial']['rt']:
            statsColumns += list(chain.from_iterable(('rt1_'+key,
                                                      'rt2_'+key)
                                                     for key in rspKeys))
            statsColumns.append('rt1_mean')
            statsColumns.append('rt2_mean')
            statsColumns.append('rt1_min')
            statsColumns.append('rt2_min')
            statsColumns.append('rt1_max')
            statsColumns.append('rt2_max')

        if config['statistics']['trial']['rtDiff']:
            statsColumns += ['rtDiff1_'+pair[0]+'-'+pair[1] for pair in rspKeyPairs]
            statsColumns += ['rtDiff2_'+pair[0]+'-'+pair[1] for pair in rspKeyPairs]

            statsColumns.append('rtDiff1_mean')
            statsColumns.append('rtDiff2_mean')

        if config['statistics']['trial']['rpt']:
            statsColumns += list(chain.from_iterable(('rpt1_'+key,
                                                      'rpt2_'+key)
                                                     for key in rspKeys))
            statsColumns.append('rpt1_mean')
            statsColumns.append('rpt2_mean')
            statsColumns.append('rpt1_min')
            statsColumns.append('rpt2_min')
            statsColumns.append('rpt1_max')
            statsColumns.append('rpt2_max')

        # Put it together
        # =====================================================================
        columns += idColumns
        columns += ixColumns
        columns += timeColumns
        columns += triggerColumns
        columns += respEvColumns
        columns += statsColumns
        columns += feedbackColumns

        return columns

    trialCols = init_trial_log(config=config,columns=list(sessColumns))

    ###########################################################################
    # BLOCK-SPECIFIC COLUMNS
    ###########################################################################

    def init_block_log(config,columns):

        # Identifiers
        # =====================================================================
        idColumns               = ['blockId']

        # Indices
        # =====================================================================
        ixColumns               = ['blockIx',
                                   'iterIx']


        nS1 = len(config['stimuli']['s1'])
        nS2 = len(config['stimuli']['s2'])

        # Accuracy - s1
        # =====================================================================
        if config['feedback']['block']['features']['s1Accuracy']['enable']:

            s1AccComprehension= [('s1Acc_%.2d' % s1,
                                  's1AccCritMet_%.2d' % s1) for s1 in range(nS1)]
            s1AccCols = list(chain(*s1AccComprehension))

        else:
            s1AccCols = []

        # Accuracy - s2
        # =====================================================================
        if config['feedback']['block']['features']['s2Accuracy']['enable']:
            s2AccComprehension= [('s2Acc_%.2d' % s2,
                                  's2AccCritMet_%.2d' % s2) for s2 in range(nS2)]
            s2AccCols = list(chain(*s2AccComprehension))
        else:
            s2AccCols = []

        # Mean RT - s1
        # =====================================================================
        if config['feedback']['block']['features']['s1MeanRt']['enable']:
            s1RtComprehension= [('s1MeanRt_%.2d' % s1,
                                 's1MeanRtCritMet_%.2d' % s1) for s1 in range(nS1)]
            s1RtCols = list(chain(*s1RtComprehension))
        else:
            s1RtCols = []

        # Mean RT diff - s1
        # =====================================================================
        if config['feedback']['block']['features']['s1MeanRtDiff']['enable']:
            s1RtDiffComprehension= [('s1MeanRtDiff_%.2d' % s1,
                                     's1MeanRtDiffCritMet_%.2d' % s1) for s1 in range(nS1)]
            s1RtDiffCols = list(chain(*s1RtDiffComprehension))
        else:
            s1RtDiffCols = []

        # Put it together
        # =====================================================================
        columns += idColumns
        columns += ixColumns
        columns += s1AccCols
        columns += s2AccCols
        columns += s1RtCols
        columns += s1RtDiffCols

        return columns

    blockCols = init_block_log(config=config,columns=list(sessColumns))

    ###########################################################################
    # OUTPUT
    ###########################################################################

    return trialCols, blockCols, sessColumns, sessData
def init_config(runtime,modDir):
    """
    Parse and process experiment configuration file.

    For details about its contents, see the experiment configurations file.

    Parameters
    ----------
    runtime     : __main__.ExperimentRuntime
                ioHubExperimentRuntime object, which brings together several aspects of the
                ioHub Event Monitoring Framework.

    modDir      : str or unicode
                directory where StPy module resides.

    Returns
    -------
    config      : dict
                specifies StPy experiment properties

    """

    config = runtime.getConfiguration()

    userDefParams = runtime.getUserDefinedParameters()

    hub = runtime.hub

    ###########################################################################
    # STUDY
    ###########################################################################

    config['study'] = {'studyId':           config['code'],
                       'taskVersionId':     config['version'],
                       'ethicsProtocolId':  config['ethics_protocol_id']
                       }

    ###########################################################################
    # SUBJECT
    ###########################################################################
    # subjectIx
    # groupIx
    # sex
    # age

    config['subject'] = {'subjectIx':   int(userDefParams['subjectIx']),
                         'groupIx':     int(userDefParams['groupIx'])}

    ###########################################################################
    # SESSION
    ###########################################################################

    tSessStartUNIX  = time.time() - core.getTime() # UNIX time stamp
    tSessStartGMT   = time.gmtime(tSessStartUNIX) # GMT time stamp

    # Seed the random number generator
    random.seed(tSessStartUNIX)

    session = {'sessionIx': int(userDefParams['sessionIx']),
               'sessionId': config['session_defaults']['name'],
               'experimenterId': config['session_defaults']['experimenterId'],
               'date': time.strftime('%Y-%m-%d',tSessStartGMT),
               'weekday': time.strftime('%a',tSessStartGMT),
               'time': time.strftime('%H%M-GMT',tSessStartGMT),
               'rngSeed': tSessStartUNIX}

    config['session'] = session

    ###########################################################################
    # LOG - PART 1: CHECK IF THE EXPERIMENTER ENTERED THE CORRECT DATA
    ###########################################################################

    groupIx         = config['subject']['groupIx']
    subjectIx       = config['subject']['subjectIx']
    sessionIx       = config['session']['sessionIx']
    studyId         = config['study']['studyId']
    taskVersionId   = config['study']['taskVersionId']
    exptDir         = os.path.abspath(os.path.join(modDir, os.pardir))

    # Make a log directory, if it does not exist
    if config['log']['dir']:
        logDir = os.path.normcase(os.path.join(config['log']['dir'],studyId))
    else:
        logDir = os.path.normcase(os.path.join(exptDir,'log/',studyId))

    if not os.path.isdir(logDir):
        os.mkdir(logDir)

    strFormatPerformance    = '%s_Study_%s_TaskVersion_%s_Group_%.2d_Subject_%.3d'

    trialLogFileName        = strFormatPerformance % ('trialLog',
                                                      studyId,
                                                      taskVersionId,
                                                      groupIx,
                                                      subjectIx)
    trialLogFile            = os.path.normcase(os.path.join(logDir, trialLogFileName + '.csv'))

    # If the file exists, check if it contains data corresponding to sessionIx
    if os.path.isfile(trialLogFile):
        groupIx     = config['subject']['groupIx']
        subjectIx   = config['subject']['subjectIx']

        trialLog = pd.read_csv(trialLogFile,
                               error_bad_lines=False)

        if sessionIx in trialLog.sessionIx.values:
            warnDlg = gui.Dlg(title="WARNING",
                              labelButtonOK=u' Continue ',
                              labelButtonCancel=u' Cancel ')
            warnDlg.addText('You specified the following settings:')
            warnDlg.addFixedField('Group index:',groupIx)
            warnDlg.addFixedField('Subject index:', subjectIx)
            warnDlg.addFixedField('Session index:',sessionIx)
            warnDlg.addText('')
            warnDlg.addText('You might have entered the wrong data. A log file with these data already exists:')
            warnDlg.addText(trialLogFile)
            warnDlg.addText('')
            warnDlg.addText('Press Continue if you want to use the above settings and overwrite/append this file.')
            warnDlg.addText('Press Cancel if you want to change settings.')

            warnDlg.show()

            if not warnDlg.OK:
                return -1



    ###########################################################################
    # APPARATUS
    ###########################################################################

    config['apparatus'] = {'hub':       hub,
                           'display':   dict(),
                           'kb':        dict(),
                           'rd':        dict(),
                           'td':        dict()}

    config['apparatus']['display']['client'] = hub.getDevice('display')
    config['apparatus']['kb']['client'] = hub.getDevice('keyboard')

    if hub.getDevice('responsedevice') is None:
        config['apparatus']['rd']['client'] = hub.getDevice('keyboard')
    else:
        config['apparatus']['rd']['client'] = hub.getDevice('responsedevice')

    if config['mritrigger']['enable']:
        trigger_port = config['mritrigger']['port']
        trigger_baud = config['mritrigger']['baud']
        config['apparatus']['td']['client'] = serial.Serial(trigger_port, trigger_baud, timeout=0.001)
        config['apparatus']['td']['settings'] = {'triggerKeys': config['mritrigger']['sync']}

        # Print and clear events from trigger port
        print(config['apparatus']['td']['client'].readlines())

    else:
        config['apparatus']['td']['client'] = None
        config['apparatus']['td']['settings'] = None

    # Keyboard settings
    # -------------------------------------------------------------------------
    escKeys = config['responses']['abortKeys']
    toggleKeys = config['responses']['toggleKeys']
    config['apparatus']['kb']['settings'] = {'escKeys': escKeys,
                                             'toggleKeys': toggleKeys}

    kb = config['apparatus']['kb']['client']

    # Response device settings
    # -------------------------------------------------------------------------
    rd = config['apparatus']['rd']['client']
    rdClass = rd.getIOHubDeviceClass()
    rspKeysPerClass = config['responses']['responseKeysPerClass']
    keyKey = {'Keyboard':   'key',
              'Serial':     'data'}
    timeKey = {'Keyboard':  'time',
               'Serial':    'time'}

    config['apparatus']['rd']['settings'] = {'class': rdClass,
                                             'rspKeys': rspKeysPerClass[rdClass],
                                             'keyKey': keyKey[rdClass],
                                             'timeKey': timeKey[rdClass]}

    # Enable event reporting and clear all recorded events
    rd.enableEventReporting()
    rd.clearEvents()

    ###########################################################################
    # WINDOW
    ###########################################################################
    display = config['apparatus']['display']['client']

    if __debug__:
        window  = visual.Window(display.getPixelResolution(),
                                monitor = display.getPsychopyMonitorName(),
                                units = 'deg',
                                fullscr = False,
                                allowGUI = False,
                                screen = display.getIndex())
    else:
        window  = visual.Window(display.getPixelResolution(),
                                monitor = display.getPsychopyMonitorName(),
                                units = 'deg',
                                fullscr = True,
                                allowGUI = False,
                                screen = display.getIndex())

    frameRate = None
    cntr = 0
    while frameRate is None:
        cntr = cntr + 1
        frameRate = window.getActualFrameRate()

        if cntr >= 3:
            print 'Cannot get frame rate after %d attempts.' % (cntr)
            print 'Terminating PsychoPy. Try and restart the program.'
            core.quit()

    frameTime = 1/frameRate
    config['window'] = {'window': window,
                        'frameRate': frameRate,
                        'frameTime': frameTime}

    ###########################################################################
    # STIMULI
    ###########################################################################

    # Make stimuli
    config['stimuli'] = {stim: define_stimulus(window,config['stimConfig'][stim],stim)
                         for stim in config['stimConfig']
                         if config['stimConfig'][stim]['content'] is not None}

    ###########################################################################
    # RESPONSES
    ###########################################################################


    ###########################################################################
    # EVALUATION
    ###########################################################################
    trialEvalData = pd.read_csv(config['evaluation']['trial']['evalDataFile'][rdClass],
                                error_bad_lines=False)
    trialEvalData = check_df_from_csv_file(trialEvalData)


    trialCategories = trialEvalData.fillna(value=np.nan)

    evalColumns = [col for col in trialEvalData.columns
                   if not col.startswith('trial')]

    config['evaluation']['trial']['evalData'] = trialEvalData[evalColumns].copy()
    config['evaluation']['trial']['correct'] = trialEvalData['trialCorrect'].copy()
    config['evaluation']['trial']['trialType'] = trialEvalData['trialType'].copy()
    config['evaluation']['trial']['responseType'] = trialEvalData['trialResponseType'].copy()
    config['evaluation']['trial']['feedback'] = trialEvalData['trialFeedback'].copy()

    ###########################################################################
    # INSTRUCTION
    ###########################################################################

    config['stimuli']['instruction'] = {type: define_stimulus(window,
                                                              config['instruction'][type])
                                        for type in config['instruction']
                                        if config['instruction'][type]['content'] is not None}



    instrListP = pd.read_csv(config['instruction']['practice']['instructionListFile'],
                             error_bad_lines=False)
    instrListP = check_df_from_csv_file(df=instrListP)
    config['instruction']['practice']['list'] = instrListP

    instrListE = pd.read_csv(config['instruction']['experiment']['instructionListFile'],
                             error_bad_lines=False)
    instrListE = check_df_from_csv_file(df=instrListE)
    config['instruction']['experiment']['list'] = instrListE

    ###########################################################################
    # PRACTICE
    ###########################################################################

    if userDefParams['practice']:
        config['practice']['enable'] = True
    else:
        config['practice']['enable'] = False

    # If a trialListFile exists, use this
    trListP = pd.read_csv(config['practice']['trialListFile'],
                          error_bad_lines=False)
    trListP = check_df_from_csv_file(df=trListP)
    config['practice']['trialList'] = trListP

    ###########################################################################
    # EXPERIMENT
    ###########################################################################

    if userDefParams['experiment']:
        config['experiment']['enable'] = True
    else:
        config['experiment']['enable'] = False

    trListE = pd.read_csv(config['experiment']['trialListFile'],
                          error_bad_lines=False)
    trListE = check_df_from_csv_file(df=trListE)
    config['experiment']['trialList'] = trListE

    ###########################################################################
    # PERFORMANCE REQUIREMENTS
    ###########################################################################

    ###########################################################################
    # CLOCK
    ###########################################################################

    config['clock'] = core.Clock()

    ###########################################################################
    # LOG - PART 2: INITIATE LOG FILES
    ###########################################################################

    # Run time info
    # -------------------------------------------------------------------------
    strFormatRuntime        = '%s_Study_%s_Group_%.2d_Subject_%.3d_Session_%.2d_%s_%s'

    if config['log']['runtime']['enable']:

        runTimeInfo = info.RunTimeInfo(win=window,
                                       refreshTest=True,
                                       verbose=True,
                                       userProcsDetailed=True)

        runTimeInfoFileName = strFormatRuntime % ('runTimeInfo',
                                       config['study']['studyId'],
                                       config['subject']['groupIx'],
                                       config['subject']['subjectIx'],
                                       config['session']['sessionIx'],
                                       config['session']['date'],
                                       config['session']['time'])

        runTimeInfoFile = os.path.normcase(os.path.join(logDir, runTimeInfoFileName + '.csv'))

        with open(runTimeInfoFile,'a+') as fileObj:
            fileObj.write(str(runTimeInfo))

    # Task performance
    # -------------------------------------------------------------------------

    # Init log data frame
    trialCols, blockCols, sessCols, sessData = init_log(config)

    config['log']['performance']['sessColumns'] = sessCols
    config['log']['performance']['sessData'] = sessData

    if config['log']['performance']['trial']['enable']:

        config['log']['performance']['trial']['columns'] = trialCols

        trialLogFileName = strFormatPerformance % ('trialLog',
                                                   config['study']['studyId'],
                                                   config['study']['taskVersionId'],
                                                   config['subject']['groupIx'],
                                                   config['subject']['subjectIx'])

        trialLogFile = os.path.normcase(os.path.join(logDir, trialLogFileName + '.csv'))

        config['log']['performance']['trial']['file'] = trialLogFile

        if not os.path.isfile(trialLogFile):
            with open(trialLogFile,'a+') as fileObj:
                DataFrame(index = [], columns = trialCols).to_csv(fileObj, index=False, header=True)

    if config['log']['performance']['block']['enable']:

        config['log']['performance']['block']['columns'] = blockCols

        blockLogFileName = strFormatPerformance % ('blockLog',
                                                   config['study']['studyId'],
                                                   config['study']['taskVersionId'],
                                                   config['subject']['groupIx'],
                                                   config['subject']['subjectIx'])

        blockLogFile = os.path.normcase(os.path.join(logDir, blockLogFileName + '.csv'))

        config['log']['performance']['block']['file'] = blockLogFile

        if not os.path.isfile(blockLogFile):
            with open(blockLogFile,'a+') as fileObj:
                DataFrame(index = [], columns = blockCols).to_csv(fileObj, index=False, header=True)

    return config
def init_stimulus(window,stimType):
    """

    Initialize PsychoPy stimulus with default settings

    Parameters
    ----------
    window      : psychopy.visual.window.Window
                PsychoPy window object, in which stimuli are presented

    stimType    : str or unicode
                stimulus type
    Returns
    -------
    stimObject  : psychopy.visual.text.TextStim or psychopy.visual.text.ImageStim
                PsychoPy stimulus object
    """

    stimDict = {'textstim': visual.TextStim(window),
                'imagestim': visual.ImageStim(window)}

    stimObject = stimDict[stimType.lower()]

    return stimObject
def present_instruction(config,type,*args):
    """
    Present instruction stimuli

    Parameters
    ----------
    config              : dict
                        specifies StPy experiment properties

    type                : str or unicode
                        block type

    blockIx             : int (optional)
                        block index

    instructionStimIx   : int (optional)
                        instruction stimulus index

    """

    # Process inputs
    # -------------------------------------------------------------------------

    # Process variable arguments
    if len(args) > 0:
        if type == 'practice' or type == 'experiment':
            blockIx = args[0]
        if type == 'blockrepeat':
            instructionStimIx = args[0]

    window          = config['window']['window']
    hub             = config['apparatus']['hub']
    rd              = config['apparatus']['rd']
    kb              = config['apparatus']['kb']
    toggleKeys      = kb['settings']['toggleKeys']
    instructionStim = config['stimuli']['instruction'][type]

    stimIx = 0

    # Determine which instruction screens to show, depending on the experiment phase
    if type == 'practice' or type == 'experiment':
        sessionIx       = config['session']['sessionIx']
        instructionList = config['instruction'][type]['list']

        pattern         = {'sessionIx': [sessionIx],
                           'blockIx':   [blockIx]}
        ix              = instructionList.index.tolist()
        iRow            = instructionList[pattern.keys()].isin(pattern).all(1)
        stim_list        = instructionList.loc[iRow,'instructionIx'].astype(int).tolist()
    elif type == 'blockrepeat':
        stim_list        = [instructionStimIx]
    elif type == 'start' or type == 'end':
        stim_list        = range(len(instructionStim))

    # Show instruction screens and monitor keyboard and response device inputs
    # -------------------------------------------------------------------------

    while stimIx < len(stim_list):

        # Clear buffer
        hub.clearEvents('all')
        rd['client'].clearEvents()
        kb['client'].clearEvents()
        noKeyPressed = True

        # Show the instruction
        instructionStim[stim_list[stimIx]].draw()
        window.flip()

        while noKeyPressed:

            # Collect responses
            rdKeyCount, toggleKeysPressed = collect_response(rd,kb,otherKeys=toggleKeys)

            # If user pressed key move to next stimulus
            if sum(rdKeyCount.values()) > 0:
                window.flip(clearBuffer=True)
                stimIx += 1
                break

            # If toggle keys are used move to next or previous stimulus
            if toggleKeysPressed:
                window.flip(clearBuffer=True)
                if toggleKeysPressed == toggleKeys[0]:
                    stimIx -= 1
                    if stimIx < 0:
                        stimIx = 0
                    break
                elif toggleKeysPressed == toggleKeys[1]:
                    stimIx += 1
                    break
def present_stimuli(window, stim_list, u, f_on_off, log):
    """
    Presents stimuli comprising a trial (fixation, cue, s1, and s2)

    Parameters
    ----------
    window      : psychopy.visual.window.Window
                PsychoPy window object, in which stimuli are presented

    stim_list   : list
                specifies a list of PsychoPy stimuli to present on this trial

    u           : numpy.ndarray
                stimulus-by-frame array specifying for each combination of
                stimulus (row) and frame (column) whether or not the stimulus
                should be displayed

    f_on_off    : numpy.ndarray
                stimulus-by-2 array specifying the frame indices of stimulus
                onset (first column) and stimulus offset (second column)

    log         : pandas.core.frame.DataFrame
                trial log

    Returns
    -------
    log         : pandas.core.frame.DataFrame
                trial log; present_stimuli fills in information about trial and
                stimulus onsets and durations, as well as differences between
                actual and planned onsets and durations

    """

    # Define dynamic variables
    # -------------------------------------------------------------------------
    n_stim  = len(stim_list)
    n_frame = np.size(u,1)
    t_flip  = [None] * (n_frame + 1)

    # Execute trial
    # =========================================================================

    # Draw stimuli, flip screen
    for frame_ix in range(n_frame):

        for stim_ix in range(n_stim -1):

            if u[stim_ix,frame_ix]:
                stim_list[stim_ix].setAutoDraw(True)
            else:
                stim_list[stim_ix].setAutoDraw(False)

        t_flip [frame_ix] = window.flip()

    # Hide all trial stimuli and present ITI stimulus
    [stim_list[stim_ix].setAutoDraw(False) for stim_ix in range(n_stim - 1)]
    stim_list[-1].setAutoDraw(True)
    t_flip [-1] = window.flip()

    # Timing
    trial_ons = t_flip [0]
    trial_off = t_flip [-1]
    trial_dur = trial_off - trial_ons

    # Actual stimulus onset and duration times
    stim_displayed = [stim.name[0:stim.name.find('_')] for stim in stim_list]

    # Log
    log.iloc[0]['trialOns'] = trial_ons
    log.iloc[0]['trialDur'] = trial_dur

    for ix in range(len(stim_displayed) - 1):
        f_on,f_off      = f_on_off[:,ix]
        ons             = t_flip [f_on] - trial_ons
        dur             = t_flip [f_off] - t_flip [f_on]
        ons_intended    = log.iloc[0][stim_displayed[ix]+'Ons']
        dur_intended    = log.iloc[0][stim_displayed[ix]+'Dur']
        ons_dt          = ons - ons_intended
        dur_dt          = dur - dur_intended

        log.iloc[0][stim_displayed[ix]+'Ons'] = ons
        log.iloc[0][stim_displayed[ix]+'Dur'] = dur
        log.iloc[0][stim_displayed[ix]+'OnsDt'] = ons_dt
        log.iloc[0][stim_displayed[ix]+'DurDt'] = dur_dt

    return log
def run_block(config,blockId,trialList,blockLog,trialOnsNextBlock):
    """
    Runs all trials comprising a block

    Parameters
    ----------
    config              : dict
                        specifies StPy experiment properties

    blockId             : str or unicode
                        identifier of the block

    trialList           : pandas.core.frame.DataFrame
                        list of trials to present

    blockLog            : pandas.core.frame.DataFrame
                        log of trials comprising the present block

    trialsOnsNextBlock  : float
                        onset of the next block (in seconds, relative to last
                        clock reset)


    Returns
    -------
    blockLog            : pandas.core.frame.DataFrame
                        block-level performance log

    allCritMet          : bool
                        whether or not all performance criteria have been met

    """

    # 1. Process inputs
    # =========================================================================

    # All relevant variables and objects
    window          = config['window']['window']
    stimuli         = config['stimuli']
    hub             = config['apparatus']['hub']
    rd              = config['apparatus']['rd']
    kb              = config['apparatus']['kb']
    td              = config['apparatus']['td']
    trialStats      = config['statistics']['trial']

    trialEvalData   = config['evaluation']['trial']
    feedbackDur     = config['feedback']['trial']['duration']
    sessColumns     = config['log']['performance']['sessColumns']
    sessData        = config['log']['performance']['sessData']

    blockIx         = trialList.iloc[0]['blockIx']

    # Define dynamic variables
    # -------------------------------------------------------------------------

    # Mock times, so that trial starts immediately
    trialTiming = {'ons':           -float('inf'),
                   'dur':           0,
                   'ITIDur':        0,
                   'refreshTime':   1/config['window']['frameRate']}
    blockOns = -float('inf')

    # =========================================================================
    trialListIxs    = trialList.index.tolist()
    trialCols       = config['log']['performance']['trial']['columns']
    trialLog        = DataFrame(index = trialListIxs,
                                columns=trialCols)

    # Present trials
    # =========================================================================

    for trialListIx in trialListIxs:

        # Prepare trial
        # ---------------------------------------------------------------------
        thisTrialLog = DataFrame(index = [trialListIx],
                                 columns = trialCols)

        # Check if scanner should trigger trial
        if config['mritrigger']['enable']:
            if 'waitForTrigger' in trialList.columns:
                waitForTrigger = trialList.ix[trialListIx]['waitForTrigger']
            else:
                waitForTrigger = False
        else:
            waitForTrigger = False

        trialOns = trialList.loc[trialListIx,'trialOns']

        # Fill in session data
        # ---------------------------------------------------------------------
        thisTrialLog.loc[trialListIx,sessColumns] = sessData

        thisTrialLog, stim_list, u, f_on_off, trial_dur = stim_to_frame_mat(config,trialList.ix[trialListIx],thisTrialLog)

        tTrialReady = config['clock'].getTime()
        print 'Trial %d ready to start: t = %f s, dt = %f ms' % (trialListIx, tTrialReady, 1000*(tTrialReady - trialOns))

        # Run trial
        # ---------------------------------------------------------------------
        thisTrialLog    = run_trial(config,
                                    waitForTrigger,
                                    trialOns,
                                    hub,
                                    thisTrialLog,
                                    trialTiming,
                                    window,
                                    stim_list,
                                    u,
                                    f_on_off,
                                    rd,
                                    kb,
                                    td,
                                    trialStats,
                                    trialEvalData,
                                    feedbackDur,
                                    stimuli)

        # Log trial data not logged inside run_trial
        # ---------------------------------------------------------------------
        thisTrialLog.loc[trialListIx,'blockId']     = blockId
        thisTrialLog.loc[trialListIx,'blockIx']     = blockIx
        thisTrialLog.loc[trialListIx,'trialIx']     = trialList.ix[trialListIx]['trialIx']

        # Session timing
        sm, ss = divmod(thisTrialLog['trialOns'].item(), 60)
        sh, sm = divmod(sm, 60)
        thisTrialLog.loc[trialListIx,'tSession']    = '%d:%02d:%02d' % (sh, sm, ss)

        # Block timing
        if trialListIx == trialListIxs[0]:
            blockOns = thisTrialLog['trialOns'].item()
        bs, bms = divmod(thisTrialLog['trialOns'].item() - blockOns,1)
        bm, bs = divmod(bs, 60)
        bh, bm = divmod(bm, 60)
        thisTrialLog.loc[trialListIx,'tBlock']      = '%d:%02d:%02d.%03d' % (bh, bm, bs,bms*1000)

        # Put trial data into data frame and file
        # ---------------------------------------------------------------------
        trialLog.ix[trialListIx] = thisTrialLog.ix[trialListIx]

        trialOns = time.time();

        with open(config['log']['performance']['trial']['file'],'a+') as fileObj:
            thisTrialLog.to_csv(fileObj, index=False, header=False, na_rep=np.nan)

        print 'Time needed to write trialLog: %.3f ms' % (1000.*(time.time() - trialOns))

    # Compute block stats
    # =========================================================================
    df = trialLog[trialLog.blockId == blockId]
    allCritMet = evaluate_block(config,
                                df=df,
                                blockId = blockId,
                                blockLog = blockLog,
                                trialOnsNextBlock=trialOnsNextBlock)

    return blockLog, allCritMet
def run_phase(config,phaseId,trialList):
    """
    Runs all trials comprising the practice or experimental phase

    Parameters
    ----------
    config      : dict
                specifies StPy experiment properties

    phaseId     : str or unicode
                phase identifier: should be either 'practice' or 'experiment'

    trialList   : pandas.core.frame.DataFrame
                list of trials to present

    """

    blockIxs        = trialList['blockIx'].unique()
    blockCols       = config['log']['performance']['block']['columns']
    blockLog        = DataFrame(index=blockIxs,
                                columns=blockCols)

    sessColumns     = config['log']['performance']['sessColumns']
    sessData        = config['log']['performance']['sessData']

    performanceReq  = config['performanceRequirements'][phaseId]

    for blockIx in blockIxs:

        allCritMet  = False
        nIter       = 0
        forceRepeat = performanceReq['forceRepeat']
        maxNIter    = performanceReq['maxNIter']

        blockId     = '%s%.3d' % (phaseId[0], blockIx)

        thisBlockLog = DataFrame(index = [blockIx],columns = blockCols)

        thisBlockLog.loc[blockIx,sessColumns] = sessData
        thisBlockLog.loc[blockIx,'blockId'] = blockId
        thisBlockLog.loc[blockIx,'blockIx'] = blockIx
        thisBlockLog.loc[blockIx,'iterX'] = nIter

        if blockIx == blockIxs[-1]:
            trialOnsNextBlock = np.inf
        else:

            nextBlockIx = [blockIxs[index + 1] for index,value in enumerate(blockIxs) if value == blockIx]
            trialList.loc[trialList['blockIx'] == nextBlockIx,'trialOns']
            trialOnsNextBlock = trialList[trialList['blockIx'] == nextBlockIx].iloc[0]['trialOns']

        while not allCritMet:

            print 'Run %s block %d' % (phaseId,blockIx)

            trialListBlock = trialList[trialList['blockIx'] == blockIx]

            present_instruction(config,phaseId,blockIx)

            thisBlockLog,allCritMet = run_block(config=config,
                                                blockId = blockId,
                                                trialList = trialListBlock,
                                                blockLog=thisBlockLog,
                                                trialOnsNextBlock=trialOnsNextBlock)

            # Write block log
            # ---------------------------------------------------------
            with open(config['log']['performance']['block']['file'],'a+') as fileObj:
                thisBlockLog.to_csv(fileObj, index=False, header=False, na_rep=np.nan)


            if forceRepeat:
                if not allCritMet:
                    if nIter == (maxNIter - 1):
                        present_instruction(config,'blockrepeat',1)
                        present_instruction(config,'end')
                        core.wait(5)
                        core.quit()
                    else:
                        nIter = nIter + 1

                        # Warn subject that block will be repeated
                        present_instruction(config,'blockrepeat',0)

                        # Reset clock to trialOns in trialList
                        # config['clock']['tracking'].reset(trialListBlock.iloc[0]['trialOns'])
                        config['clock'].reset(trialListBlock.iloc[0]['trialOns'])
            else:
                break
def run_trial(config,waitForTrigger,trialOns,hub,trialLog,trialTiming,window,stim_list,u,f_on_off,rd,kb,td,trialStats,trialEvalData,feedbackDur,stimuli):
    """
    Runs a trial

    Parameters
    ----------
    config          : dict
                    specifies StPy experiment properties

    waitForTrigger  : bool
                    whether or not trial onsent is contingent on trigger

    trialOns        : int or float
                    trial onset (in seconds from clock reset)

    hub             : psychopy.iohub.client.ioHubConnection
                    interface to the ioHub

    trialLog        : pandas.core.frame.DataFrame
                    empty trial log

    trialTiming     : dict
                    specifies timing properties, such as trial onset, trial
                    duration, inter-trial interval duration, and refresh times

    window          : psychopy.visual.window.Window
                    PsychoPy window object, in which stimuli are presented

    stim_list       : list
                    list of PsychoPy stimuli

    u               : numpy.ndarray
                    stimulus-by-frame array specifying for each combination of
                    stimulus (row) and frame (column) whether or not the
                    stimulus should be displayed

    f_on_off        : numpy.ndarray
                    stimulus-by-2 array specifying the frame indices of
                    stimulus onset (first column) and stimulus offset (second
                    column)

    rd              : dict
                    specifies response device properties

    kb              : dict
                    specifies keyboard properties

    td              : dict
                    specifies trigger device properties

    trialStats      : dict
                    specifies which descriptive statistics need to be computed

    trialEvalData   : dict
                    specifies all data necessary to evaluate trials

    feedbackDur     : int or float
                    duration of trial feedback (in seconds)

    stimuli         : dict
                    all stimuli used in the experiment

    Returns
    -------
    trialLog        : pandas.core.frame.DataFrame
                    trial log


    """

    # Wait for external trigger, or trial onset, or both
    # -------------------------------------------------------------------------
    if waitForTrigger:
        triggered = None
        triggerKeys = td['settings']['triggerKeys']

        # Clear buffer
        td['client'].readlines()

        while not triggered:
            triggerEvents = td['client'].readline()

            for ev in triggerEvents:
                print 'Trigger received: %s' % (ev)

                if any([re.findall(key,ev) for key in triggerKeys]):
                    triggered = True

    if trialOns == 0:
        # If this is the start of a session or block
        config['clock'].reset()
    while config['clock'].getTime() < (trialOns - 1.5*trialTiming['refreshTime']):
        pass

    tStart = config['clock'].getTime()

    # Clear events
    # -------------------------------------------------------------------------
    hub.clearEvents('all')

    if __debug__:
        tEventsCleared = config['clock'].getTime()
        print '* Events cleared: t = %f ms; dt = %f ms' % \
              (1000*(tEventsCleared-tStart),1000*(tEventsCleared-tStart))

    # Present stimuli
    # -------------------------------------------------------------------------
    trialLog = present_stimuli(window=window,
                               stim_list=stim_list,
                               u=u,
                               f_on_off=f_on_off,
                               log=trialLog)

    if __debug__:
        tStimPresented = config['clock'].getTime()
        print '* Stimuli presented: t = %f ms, dt = %f ms' % \
              (1000*(tStimPresented-tStart),1000*(tStimPresented-tEventsCleared))

    # Collect responses
    # -------------------------------------------------------------------------
    trialLog = collect_response(rd=rd,
                                kb=kb,
                                log=trialLog)

    if __debug__:
        tRespCollected = config['clock'].getTime()
        print '* Responses collected: t = %f ms, dt = %f ms' % \
              (1000*(tRespCollected-tStart),1000*(tRespCollected-tStimPresented))

    # Compute trial statistics
    # -------------------------------------------------------------------------
    trialLog = compute_trial_statistics(trialStats=trialStats,
                                        rd=rd,
                                        log=trialLog)

    if __debug__:
        tStatsComputed = config['clock'].getTime()
        print '* Stats computed: t = %f ms, dt = %f ms' % \
              (1000*(tStatsComputed-tStart),1000*(tStatsComputed-tRespCollected))

    # Evaluate trial
    # -------------------------------------------------------------------------
    trialLog = evaluate_trial(evalData=trialEvalData,
                              feedbackDur=feedbackDur,
                              window=window,
                              stimuli=stimuli,
                              log=trialLog)

    if __debug__:
        tFeedbackGiven = config['clock'].getTime()
        print '* Feedback given: t = %f ms, dt = %f ms' % \
              (1000*(tFeedbackGiven-tStart),1000*(tFeedbackGiven-tStatsComputed))

    # Wrap up
    # -------------------------------------------------------------------------
    return trialLog
def set_soa(config,log):
    """
    <SUMMARY LINE>

    <EXTENDED DESCRIPTION>

    Parameters
    ----------
    <NAME> : <TYPE>
        <DESCRIPTION>

    Returns
    -------
    <NAME> : <TYPE>
        <DESCRIPTION>

    Raises
    ------
    <EXCEPTIONS>

    Usage
    -----
    <USAGE>

    Example
    -------
    <EXAMPLE THAT CAN IDEALLY BE COPY PASTED>
    """

    # Process inputs, define variables
    # -------------------------------------------------------------------------
    fTime = config['window']['frameTime']

    soaIx = config['experiment']['trialList']['soaIx'].dropna().unique()
    nSoa = len(soaIx)

    # Identify no-signal trials
    iNS = performanceLog.s1Ix.notnull() & performanceLog.s2Ix.isnull()

    # Response time data from first response
    rtCols = [col for col in list(performanceLog) if col.startswith('rt1')]
    rtData = performanceLog[rtCols]
    meanRt = rtData.mean().mean()

    # Proportion steps
    propStep = {2: .75, # .15, .90 of meanRT
                3: .40, # .15, .55, .95 of meanRT
                4: .25, # .15, .40, .65, .90 of meanRT
                5: .20, # .15, .35, .55, .75, .95 of meanRT
                6: .15} # .15, .25, .35, .45, .55, .65, .75 of meanRT

    # Determine new SOAs
    soa1        = np.around(meanRt * .15 / fTime) * fTime
    soaStep     = np.around(meanRt * propStep(min([nSoa,6])) / fTime) * fTime
    soa         = np.linspace(soa1,soa1+(nSoa-1)*propStep,nSoa)

    # Update soa experiment trial list
    for ix in range(nSoa):
        pass
def time_to_frame(ons, dur, dt, trial_dur):
    """
    Makes a stimulus-frame array based on stimulus onsets and durations

    Parameters
    ----------
    ons         : numpy.ndarray
                1D-array of stimulus onset(s)

    dur         : numpy.ndarray
                1D-array of stimulus duration(s)

    dt          : numpy.ndarray
                time step (in seconds)

    trial_dur   : numpy.ndarray
                trial duration (in seconds), based on onsets and durations of
                the fixation, cue, s1, and s2 stimulus.

    Returns
    -------
    u           : numpy.ndarray
                stimulus-by-frame array specifying for each combination of
                stimulus (row) and frame (column) whether or not the stimulus
                should be displayed

    f_on_off    : numpy.ndarray
                stimulus-by-2 array specifying the frame indices of stimulus
                onset (first column) and stimulus offset (second column)

    t           : numpy.ndarray
                array of frame onset times (in seconds, relative to trial
                onset)

    Raises
    ------
    AssertionError:
        If 'ons' is not instance of class np.ndarray
        If 'dur' is not instance of class np.ndarray
        If 'dt' is not instance of class np.ndarray
        If 'trial_dur' is not instance of class np.ndarray

    """

    ###########################################################################
    # 1. PROCESS INPUTS & SPECIFY VARIABLES
    ###########################################################################

    # 1.1. Import libraries
    # =========================================================================


    # 1.2. Process inputs
    # =========================================================================
    # Check if all inputs are ndarrays

    assert isinstance(ons, np.ndarray), 'ons should be of type ndarray'
    assert isinstance(dur, np.ndarray), 'dur should be of type ndarray'
    assert isinstance(dt, np.ndarray), 'dt should be of type ndarray'
    assert isinstance(trial_dur, np.ndarray), 'trial_dur should be of type ndarray'

    #TODO: assert that inputs are no unsized objects;

    # 1.3. Define dynamic variables
    # =========================================================================
    # Number of stimuli
    n_stim = np.size(ons)

    # Number of frames
    n_frame = int(np.ceil(trial_dur/dt))

    # Array of frames
    f = range(0, n_frame, 1)

    # Array of time points
    t = np.linspace(0, n_frame * float(dt), n_frame, True)

    # Stimulus onsets and offsets, in frames
    f_on = np.around(ons/dt).astype(int)
    f_off = np.around((ons + dur)/dt).astype(int)

    # Preallocate u
    u = np.zeros((n_stim, n_frame)).astype(int)

    ###########################################################################
    # 2. SPECIFY STIMULUS AND INPUT MATRICES
    ###########################################################################

    # Loop over stimuli
    for i_stim in range(0, n_stim):

        # Stimulus onsets in stimulus-frame diagram
        u[i_stim, f == f_on[i_stim]] += 1

        # Stimulus offsets in stimulus-frame diagram
        u[i_stim, f == f_off[i_stim]] -= 1

    # Encode 'stimulus on' as 1.0, 'stimulus off' as 0.0
    u = np.cumsum(u, axis=1)

    # Convert to boolean
    u = u.astype(bool)

    # Stimulus on- and offset in frames
    f_on_off = np.vstack([f_on,f_off])

    ########################################
    # 3. SPECIFY OUTPUT
    ########################################
    return u, f_on_off, t