import decimal
import itertools
import os
import pathlib
import re

import canmatrix
import click.testing
import pytest

import epyqlib.tests.common

import epcpm.cli.importsym
import epcpm.cli.exportsym
import epcpm.importexport
import epcpm.importexportdialog


round_trip = pathlib.Path(__file__).parents[3] / 'roundtrip'
project = round_trip / 'project.pmp'
example_device = epyqlib.tests.common.new_devices()[('develop', 'factory')]
exported_can = (
        round_trip / 'exported'
).with_suffix(example_device.can.suffix)
exported_hierarchy = (
        round_trip / 'hierarchy.parameters.json'
).with_suffix(example_device.hierarchy.suffix)


def _full_round_trip():
    # directory = pathlib.Path('full_import')
    # paths = epcpm.importexportdialog.paths_from_directory(directory)
    # project = epcpm.importexport.full_import(paths=paths)
    import epcpm.project
    project = epcpm.project.loadp(pathlib.Path('full_import')/'project.pmp')

    directory = pathlib.Path(os.sep)/'epc'/'g'/'36'/'grid-tied'
    paths = epcpm.importexportdialog.paths_from_directory(directory)

    epcpm.importexport.full_export(project=project, paths=paths, first_time=True)

    # project = epcpm.importexport.full_import(paths=paths)
    # epcpm.importexport.full_export(project=project, paths=paths)


@pytest.mark.skip
def test_import():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.importsym.cli,
        [
            '--sym', example_device.can,
            '--hierarchy', example_device.hierarchy,
            '--project', project,
            '--can', round_trip / 'can.json',
            '--parameters', round_trip / 'parameters.json',
            '--sunspec', round_trip / 'sunspec.json',
            '--add-tables',
            '--add-sunspec-types',
        ],
        catch_exceptions=False,
    )
    print(result.output)

    assert result.exit_code == 0


@pytest.mark.skip
def test_export():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.exportsym.cli,
        [
            '--project', project,
            '--sym', exported_can,
            '--hierarchy', exported_hierarchy,
        ],
        catch_exceptions=False,
    )
    print(result.output)

    assert result.exit_code == 0


def normalized_attributes(attributes):
    attributes = dict(attributes)

    if 'GenSigStartValue' in attributes:
        attributes['GenSigStartValue'] = decimal.Decimal(
            attributes['GenSigStartValue'],
        )

    return attributes


def assert_signals_equal(
        original,
        original_frame,
        exported,
        exported_frame,
):
    print(
        original_frame.name,
        original_frame.mux_names.get(original.multiplex),
        original.name,
    )
    assert_attributes_equal(
        original=original,
        exported=exported,
        attributes=(
            'enumeration',
            'is_float',
            'is_little_endian',
            'is_multiplexer',
            'is_signed',
            'max',
            'min',
            'multiplex',
            'factor',
            'offset',
            'size',
            'startBit',
            'unit',
        ),
    )

    tweaked = dict(exported.attributes)
    if 'LongName' not in original.attributes:
        tweaked.pop('LongName', None)

    tweaked_attributes = normalized_attributes(tweaked)
    original_attributes = normalized_attributes(original.attributes)

    if 'GenSigStartValue' in original_attributes:
        diff = abs(
            tweaked_attributes.pop('GenSigStartValue')
            - original_attributes.pop('GenSigStartValue')
        )
        assert diff < 1

    assert tweaked_attributes == original_attributes, original.name

    factory = '<factory>'
    configs = ('<HY>', '<MG3>', '<MG4>', '<DG>', '<DC>')

    def split_and_access_level(comment):

        split = comment.split()

        return (
            factory in split,
            (
                tag in split
                for tag in configs
            ),
            [x for x in split if x not in (factory, *configs)],
        )

    original_factory, original_configs, original_comment = (
        split_and_access_level(original.comment)
    )
    exported_factory, exported_configs, exported_comment = (
        split_and_access_level(exported.comment)
    )

    assert exported_comment == original_comment, original.name

    not_applicable = (
        'readparam_command',
        'readparam_status',
        'meta',
    )
    if original.name.casefold() not in not_applicable:
        original_mux = [
            x for x in original_frame.signals if x.multiplex == 'Multiplexor'
        ]
        original_mux, = original_mux if original_mux else (None,)

        exported_mux = [
            x for x in exported_frame.signals if x.multiplex == 'Multiplexor'
        ]
        exported_mux, = exported_mux if exported_mux else (None,)

        if original_mux is None:
            assert exported_mux == original_mux, original.name

        def tagged_including_mux_check(tag, tagged, signal, mux):
            if mux is not None:
                return (
                        tagged
                        or (
                                signal is not mux
                                and tag in mux.comments[
                                    signal.multiplex]
                        )
                )

            return (
                    tagged
                    or tag in original_frame.comment
            )

        original_access_level = tagged_including_mux_check(
            tag=factory,
            tagged=original_factory,
            signal=original,
            mux=original_mux,
        )
        exported_access_level = tagged_including_mux_check(
            tag=factory,
            tagged=exported_factory,
            signal=exported,
            mux=exported_mux,
        )

        assert exported_access_level == original_access_level, original.name

        z = zip(configs, original_configs, exported_configs)
        for config, original_tagged, exported_tagged in z:
            original_config = tagged_including_mux_check(
                tag=config,
                tagged=original_tagged,
                signal=original,
                mux=original_mux,
            )
            exported_config = tagged_including_mux_check(
                tag=config,
                tagged=exported_tagged,
                signal=exported,
                mux=exported_mux,
            )

            assert exported_config == original_config, (config, exported.comment, original.comment, original.name)

    assert_varied_dict_equal(original.values, exported.values)

    assert exported_comment == original_comment, original.name


def get_name(x):
    return x.name


def sorted_names(names):
    return sorted(names, key=lambda x: (x.casefold(), x))


def unvary_signal_names(name):
    changes = (
        (r'(IGBT|Diode)_R(\d)', r'\1_r\2'),
        (r'(IGBT|Diode)_Tc(\d)', r'\1_tc\2'),
        ('Rii', 'rii'),
        ('Rdi', 'rdi'),
        ('Alpha', 'alpha'),
        ('Amps', 'amps'),
        ('Beta', 'beta'),
        (r'Leg(\d)', r'leg\1'),
        ('CurrentLCL', 'currentLCL'),
        ('MinPulseTime', 'minPulseTime'),
        ('N15V_Supply', 'n15V_Supply'),
        (r'V([p\d]+)_Supply', r'v\1_Supply'),
        ('Phase([ABC])', r'phase\1'),
        ('PostTriggerDuration_S', 'PostTriggerDuration_s'),
        (r'LegInductance(\d)', r'legInductance\1'),
        ('TempSetpoint', 'tempSetpoint'),
        ('LineCurrentLimit', 'lineCurrentLimit'),
        ('Dc(Current|Voltage)Limit', r'dc\1Limit'),
        ('Dc(Current|Voltage)Limit_Echo', r'dc\1Limit_echo'),
        ('Line(Current|Voltage)Limit_Echo', r'line\1Limit_echo'),
        ('PpcIslDroop([VF])_IBpt', r'PpcIslDroop\1_iBpt'),
        ('PpcIslDroop([VF])_DBpt', r'PpcIslDroop\1_dBpt'),
        ('PpcIslDroop([VF])_QBpt', r'PpcIslDroop\1_qBpt'),
        ('PpcIslDestab([VF])_VBpt', r'PpcIslDestab\1_vBpt'),
        ('PpcIslDestab([VF])_DBpt', r'PpcIslDestab\1_dBpt'),
        ('PpcIslDestab([VF])_QBpt', r'PpcIslDestab\1_qBpt'),
        ('PpcIslDestab([VF])_FBpt', r'PpcIslDestab\1_fBpt'),
        ('Ig_Max', 'Ig_max'),
        (
            r'(MesdConfigLutCalibration_)T(Igbt|Aux|Motor)_(\d+)',
            r'\1t\2_\3',
        ),
        (
            '(ProtTemperatureLimitTrip_)T({})_(Running|Stopped)'.format(
                '|'.join((
                    'Inverter',
                    'Internal',
                    'Device',
                    'Inlet',
                    'Delta',
                )),
            ),
            lambda m: f'{m.group(1)}t{m.group(2)}_{m.group(3).casefold()}',
        ),
        (
            '(ProtCtrlVoltageLimitTrip)_V(Pos|Neg)(24|15|5|3)',
            r'\1_v\2\3',
        ),
        (r'(.*)_TxRate', r'\1_txRate'),
        *(
            (x, lambda m: m.group(0)[0].casefold() + m.group(0)[1:])
            for x in (
                'DIg',
                'DpwmStrategy',
                'DcGroup',
                'D[012]',
                'F[012]',
                'Q([012]|Ig)',
                'V([012])',
                '(F|V|W|XpVa)Tau',
                'AcGroup',
                '(C|G)(L|R)s',
                'AcHalfPeriodTrack',
                'DtCompEnable',
                'DutyLimit',
                'EeSaveInProgress',
                'EntryPulseNr',
                'FCut(F|Ig|V|Vg)',
                'FDev(H|L)',
                'FMax',
                'FMin',
                'FNom',
                'FourWireEnable',
                'FSw(Hysteresis|Minimum|Request)',
                'I([012]|Abs|Delta|Dlt)',
                'Ind(IslStart|Threshold)',
                'K(Alpha|Apply|Phi|Vq)',
                'Limit(XY|Z)',
                'Lim(Lower|Upper)',
                'Load(L|PhiTau|R)',
                'Min(Current|VectorTime|Volt)',
                'ModDepthLimit(Beg|End)',
                'NetworkFrequency',
                'P(Delta|PhaseSel)',
                'PhaseSel',
                'PhiAbs',
                'Sat(CompEnable|Voltage)',
                'S(C|R)s',
                'SRv',
                'SimModeEnable',
                'SpectrumAdjustTau',
                'SpreadSpect(Enable|Inject)',
                'StandardDeviation',
                'SyncMod(Enable|Strategy)',
                'Tau',
                'T(Adapt|Deadband|Delta)',
                'Threshold',
                'TimeConst',
                'TrigCalTime',
                'TripTime',
                'TSwitch',
                'U',
                'VDelta',
                'VectAlignCtrl_(K[dp]|StepSat|Ti)',
                'V(Max|Min)',
                'VoltMag',
                'VsComp(Enable|Tau)',
                'Y',
                'ZeroVectorStrategy',
            )
        ),
        *(
            (
                r'(.*)_({x})_(.*)'.format(x=x),
                lambda
                    m: f'{m.group(1)}_{m.group(2).casefold()}_{m.group(3)}',
            )
            for x in (
                'Seconds',
                'Hertz',
                'Percent_Nominal_Volts',
                'Percent_Nominal_Var',
                'Percent_Nominal_Pwr',
                'Percent',
                'Nominal_Volts',
            )
        ),
        *(
            (x, lambda m: m.group(1) + m.group(2) + m.group(3).casefold())
            for x in (
                '(DcCurrent|DcVoltage|ReactivePower|RealPower)()(Limit|_Echo)',
                '(ReadParam|SaveToEE)(_)(Command|Status)',
                '(TempTmodel)(_)(Calculated)',
                '({})(_)(Echo)'.format(
                    '|'.join((
                        'Enable',
                        'FaultClr',
                        'WarningClr',
                        'ReactiveCurrent',
                        'RealCurrent',
                        'IslandReconnect',
                    )),
                ),
                '({})(_)(Measured)'.format(
                    '|'.join((
                        'TempDeviceBrdg[ABC]',
                        'CurrentAC',
                        'Frequency',
                        'VoltageAC',
                        'FrequencyRemote',
                        'VoltageAcRemote',
                        'SolarCurrent',
                        'SolarVoltage',
                        'CurrentDC',
                        'VoltageDCBus',
                        'VoltageDCInput',
                        'L[123]Current',
                        'L[123]ToL[123]Voltage',
                        '.*',
                    )),
                ),
        )
        ),
    )

    tweaked = name
    for pattern, replacement in changes:
        tweaked = re.sub(f'^{pattern}$', replacement, tweaked)

    return tweaked


def assert_signal_list_equal(
        original,
        original_frame,
        exported,
        exported_frame,
):
    original_names = sorted_names(
        x.name
        for x in original
    )
    exported_names = sorted_names(
        unvary_signal_names(x.name)
        for x in exported
    )

    case_insensitive = (
        'aclosshotstandbydc',
        'aclosshotstandbypc',
        'acwaitenabledcatref',
        'argadjust',
        'argerrmax',
        'argerrsat',
        'argerrtau',
        'autodisconnectongridloss',
        'autofollowingpostconnect',
        'autoreconnectongridavail',
        'autosequencewhendisabled',
        'autovolttrackduringsynch',
        'conntimeout',
        'controlsvariant',
        'current',
        'dcwaitenabledcatref',
        'disctimeout',
        'enabledelayac',
        'enabledelaydc',
        'didt',
        'dqccterm',
        'dummy',
        'freq',
        'fswactual',
        # 'ftau',
        'gain',
        'groupedenable',
        'hardwarevariant',
        'level',
        'limit',
        'magadjust',
        'magerrmax',
        'magerrtau',
        'moddepthxy',
        'moddepthz',
        'max',
        'min',
        'pllenable',
        'pulsenractual',
        'r',
        'rate',
        'resistance',
        'syncactive',
        'syncholdtime',
        'synctimeout',
        'tc',
        'temp',
        'temperature',
        'time',
        'tisllatch',
        'tunload',
        'vdevh',
        'vdevl',
        'volts',
        # 'vtau',
        # 'wtau',
    )

    zipped = itertools.zip_longest(original_names, exported_names)
    for original_name, exported_name in zipped:
        if original_name.casefold() in case_insensitive:
            assert (
                exported_name.casefold()
                == original_name.casefold()
            ), original.name
        else:
            assert exported_name == original_name

    def key(x):
        return (
            x.name.casefold(), x.multiplex
            if x.multiplex is not None
            else float('-inf')
        )

    zipped = itertools.zip_longest(
        sorted(original, key=key),
        sorted(exported, key=key),
    )
    for original_signal, exported_signal in zipped:
        assert_signals_equal(
            original=original_signal,
            original_frame=original_frame,
            exported=exported_signal,
            exported_frame=exported_frame,
        )


def assert_attributes_equal(original, exported, *, attributes):
    for attribute in attributes:
        assert (
            getattr(exported, attribute) == getattr(original, attribute)
        ), (original.name, attribute)


def assert_varied_dict_equal(original, exported):
    zipped = itertools.zip_longest(
        sorted(original.items()),
        sorted(exported.items()),
    )
    for (original_value, original_name), (exported_value, exported_name) in zipped:
        assert exported_value == original_value

        tweaked = unvary_signal_names(exported_name)
        assert tweaked == original_name


def assert_frames_equal(original, exported):
    assert_attributes_equal(
        original=original,
        exported=exported,
        attributes=(
            'name',
            'id',
            'extended',
            'attributes',
            'comment',
            'is_multiplexed',
            'size',
        ),
    )

    assert_varied_dict_equal(original.mux_names, exported.mux_names)

    assert_signal_list_equal(
        original=original.signals,
        original_frame=original,
        exported=exported.signals,
        exported_frame=exported,
    )


def collect_attribute(sequence, name):
    return {getattr(x, name) for x in sequence}


def assert_frame_lists_equal(original, exported):
    original_names = collect_attribute(original, 'name')
    exported_names = collect_attribute(exported, 'name')

    assert exported_names == original_names, original.name

    zipped = itertools.zip_longest(
        sorted(original, key=get_name),
        sorted(exported, key=get_name),
    )
    for original_frame, exported_frame in zipped:
        assert_frames_equal(original_frame, exported_frame)


def assert_value_tables_equal(original, exported):
    return exported == original


@pytest.mark.skip
def test_roundtrip():
    original, = canmatrix.formats.loadp(os.fspath(example_device.can)).values()
    assert original.load_errors == []
    exported, = canmatrix.formats.loadp(os.fspath(exported_can)).values()
    assert exported.load_errors == []

    assert_frame_lists_equal(original.frames, exported.frames)
    assert_value_tables_equal(original.valueTables, exported.valueTables)
