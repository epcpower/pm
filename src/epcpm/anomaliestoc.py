import attr

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.c
import epcpm.pm_helper
import epcpm.anomalymodel


builders = epyqlib.utils.general.TypeMap()


def export(anomaly_model, parameters_model, h_path):

    builder = epcpm.anomaliestoc.builders.wrap(
        wrapped=anomaly_model.root,
        parameter_uuid_finder=parameters_model.node_from_uuid,
    )

    data = builder.gen()

    epcpm.c.render(
        source=h_path.with_suffix(f"{h_path.suffix}_pm"),
        destination=h_path,
        context={"anomaly_tables": data},
    )


@builders(epcpm.anomalymodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):

        items = []
        for anomaly_table in self.wrapped.children:
            item = builders.wrap(
                wrapped=anomaly_table,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()
            items.append(item)

        return items


@builders(epcpm.anomalymodel.AnomalyTable)
@attr.s
class AnomalyTable:

    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        items = []
        for anomaly in self.wrapped.children:
            item = builders.wrap(
                wrapped=anomaly,
                parameter_uuid_finder=self.parameter_uuid_finder,
                table_abbreviation=self.wrapped.abbreviation,
            ).gen()
            items.append(item)
        return {"anomalies": items, "abbreviation": self.wrapped.abbreviation}


@builders(epcpm.anomalymodel.Anomaly)
@attr.s
class Anomaly:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    table_abbreviation = attr.ib()

    def gen(self):

        # Construct enumerator name
        enum_name = "{:s}_ANOMALY_{:s}".format(
            self.table_abbreviation, self.wrapped.abbreviation
        )

        # Resolve response level and trigger type names
        resp_level_A = self.parameter_uuid_finder(
            self.wrapped.response_level_A
        ).abbreviation
        resp_level_I = self.parameter_uuid_finder(
            self.wrapped.response_level_I
        ).abbreviation
        trig_type = self.parameter_uuid_finder(self.wrapped.trigger_type).abbreviation

        return {
            "abbreviation": self.wrapped.abbreviation,
            "enum_name": enum_name,
            "name": self.wrapped.name,
            "code": self.wrapped.code,
            "trigger_type": trig_type,
            "response_level_I": resp_level_I,
            "response_level_A": resp_level_A,
        }
