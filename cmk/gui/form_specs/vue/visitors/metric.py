#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.visitors.string import StringVisitor
from cmk.gui.i18n import _

from ._type_defs import EmptyValue


class MetricVisitor(StringVisitor):
    def _to_vue(
        self, raw_value: object, parsed_value: str | EmptyValue
    ) -> tuple[shared_type_defs.Metric, str]:
        string_autocompleter, value = super()._to_vue(raw_value, parsed_value)
        string_autocompleter_args = asdict(string_autocompleter)
        del string_autocompleter_args["type"]
        return (
            shared_type_defs.Metric(
                **string_autocompleter_args,
                host_filter_autocompleter=shared_type_defs.Autocompleter(
                    data=shared_type_defs.AutocompleterData(
                        ident="config_hostname",
                        params=shared_type_defs.AutocompleterParams(
                            strict=True, escape_regex=False
                        ),
                    ),
                ),
                service_filter_autocompleter=shared_type_defs.Autocompleter(
                    data=shared_type_defs.AutocompleterData(
                        ident="config_service_description",
                        params=shared_type_defs.AutocompleterParams(
                            show_independent_of_context=True, strict=True, escape_regex=False
                        ),
                    ),
                ),
                i18n=shared_type_defs.MetricI18n(
                    host_input_hint=_("(Select host)"),
                    host_filter=_("Filter selection by host name:"),
                    service_input_hint=_("(Select service)"),
                    service_filter=_("Filter selection by service:"),
                ),
            ),
            value,
        )
