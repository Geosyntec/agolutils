import json
import warnings
from pathlib import Path
from typing import List, Optional, Union

import pandas

from arcgis import gis

from agolutils.utils import make_path, yesterday, tomorrow
from agolutils.context import write_context
from .utils import get_content


warnings.filterwarnings("ignore", message=".*'infer_datetime_format' is deprecated.*")


def build_survey123_contexts(
    config,
    oids,
    env: Optional[Union[str, Path]] = None,
    context_file_pattern=None,
):
    if context_file_pattern is None and "context_file_pattern" in config:
        context_file_pattern = config["context_file_pattern"]

    itemid = config.get("connection", {}).get("survey123", {}).get("service_id", None)

    obj = get_content(itemid=itemid, config=config, env=env)
    surveys = Survey123Service(obj)

    context_paths = surveys.write_contexts(
        oids,
        context_file_pattern=context_file_pattern,
    )

    return context_paths


def download_attachment(
    layer: gis.Layer,
    oid: int,
    attachment_id: int,
    save_path: str = "./",
    filename_prefix: Optional[str] = None,
) -> Path:
    if not layer.properties.hasAttachments:
        raise ValueError("No Attachments to download.")

    layer.attachments.download(  # type: ignore
        oid=oid, attachment_id=attachment_id, save_path=save_path
    )
    att = next(
        filter(
            lambda att: att["id"] == attachment_id,
            layer.attachments.get_list(oid=oid),  # type: ignore
        )
    )
    name = att["name"]

    old_name = Path(save_path).resolve() / name

    if filename_prefix is not None:
        new_name = Path(save_path).resolve() / (filename_prefix + name)
        old_name.replace(new_name)
        return new_name
    return old_name


def download_all_attachments(
    layer: gis.Layer,
    oid: int,
    save_path: Optional[str] = None,
) -> List[Path]:
    files = []

    attachments = []
    if layer.properties.hasAttachments:
        attachments = layer.attachments.get_list(oid=oid)  # type: ignore
    name = layer.properties.name + "-"
    for att in attachments:
        attachment_id = att["id"]
        f = download_attachment(
            layer,
            oid=oid,
            attachment_id=attachment_id,
            save_path=save_path or "./",
            filename_prefix=name,
        )

        files.append(f)

    return files


def get_layer_records_by_objectid(layer, oids: List[int]):
    object_ids = ",".join(map(str, oids))
    q = layer.query(object_ids=object_ids, return_geometry=False)
    df = q.sdf
    return json.loads(df.to_json(orient="records"))


def get_layer_by_prop(service, prop, equals):
    fxn = lambda x: x.properties.get(prop) == equals  # noqa: E731
    return next(filter(fxn, service.layers + service.tables))


def get_related_tables(service, layer):
    tables = []
    for relationship in layer.properties.relationships:
        rel_id = relationship["id"]
        tableid = relationship["relatedTableId"]
        table = get_layer_by_prop(service, "id", tableid)
        tables.append({"rel_id": rel_id, "table": table})
    return tables


def get_related_records(
    layer, oid, context_dir, service=None, tables=None, download_attachments=True
):
    relates = {}

    if tables is None:
        tables = get_related_tables(service, layer)

    for rel in tables:
        rel_id = rel["rel_id"]
        table = rel["table"]
        name = table.properties.name

        related_record_groups = layer.query_related_records(oid, rel_id).get(
            "relatedRecordGroups", []
        )
        rel_oids = []
        for g in related_record_groups:
            for record in g["relatedRecords"]:
                rel_oids.append(record["attributes"]["objectid"])

        if not rel_oids:
            return relates

        files = []
        if download_attachments and table.properties.hasAttachments:
            for rel_oid in rel_oids:
                save_path = Path(context_dir)
                attachment_filepaths = download_all_attachments(
                    table, rel_oid, save_path=context_dir
                )
                files.extend(
                    [
                        {
                            "objectid": rel_oid,
                            "attachment_filepath": str(
                                f.relative_to(save_path.resolve())
                            ),
                        }
                        for f in attachment_filepaths
                    ]
                )

        rel_df = table.query(
            object_ids=",".join(map(str, rel_oids)), return_geometry=False
        ).sdf
        if files:
            rel_df = rel_df.merge(pandas.DataFrame(files), on="objectid")

        rel_df["__layer_properties"] = json.loads(
            json.dumps(slim_layer_properties(table.properties))
        )

        data = json.loads(rel_df.to_json(orient="records"))
        for dct in data:
            dct["__layer_properties"] = slim_layer_properties(table.properties)
        relates[name] = {"name": name}
        relates[name]["data"] = data
        relates[name]["__layer_properties"] = slim_layer_properties(table.properties)

    return relates


def slim_layer_properties(props: dict):
    keys = [
        "id",
        "name",
        "type",
        "serviceItemId",
        "description",
        "hasAttachments",
        "fields",
        "relationships",
        "dateFieldsTimeReference",
    ]

    return {k: v for k, v in props.items() if k in keys}


def get_contexts(
    layer,
    oids,
    context_file_pattern=None,
    download_attachments=True,
    get_relates=True,
    tables=None,
    service=None,
):
    records = get_layer_records_by_objectid(layer, oids)
    if context_file_pattern is None:
        context_file_pattern = "contexts/{globalid}.json"

    contexts = []
    for record in records:
        context = record
        outpath = make_path(context_file_pattern.format(**context))
        outdir = outpath.parent

        oid = context["objectid"]
        context["__layer_properties"] = slim_layer_properties(layer.properties)
        context["_layer_name"] = context["__layer_properties"].get(
            "name", "no-layer-name"
        )
        context["_filepath"] = outpath

        if get_relates:
            context["relates"] = get_related_records(
                layer,
                oid,
                context_dir=outdir,
                tables=tables,
                service=service,
                download_attachments=download_attachments,
            )

        if download_attachments and layer.properties.hasAttachments:
            attachments = layer.attachments.get_list(oid)
            for att in attachments:
                file = download_attachment(
                    layer,
                    oid=oid,
                    attachment_id=att["id"],
                    save_path=str(outdir),
                    filename_prefix=context["_layer_name"] + "-",
                )

                att["attachment_filepath"] = str(file.relative_to(outdir.resolve()))
            context["attachments"] = attachments

        contexts.append(context)

    return contexts


def get_recent(layer, related_tables=None, start_date=None, end_date=None):
    if related_tables is None:
        related_tables = []
    if start_date is None:
        start_date = yesterday()
    if end_date is None:
        end_date = tomorrow()

    edit_field = layer.properties["editFieldsInfo"]["editDateField"]
    time_query = "{e} >= DATE '{start_date}' and {e} <= DATE '{end_date}'"

    globalids = None

    if related_tables:
        dfs = []
        for t in related_tables:
            tedit_field = t["table"].properties["editFieldsInfo"]["editDateField"]
            sdf = (
                t["table"]
                .query(
                    time_query.format(
                        e=tedit_field, start_date=start_date, end_date=end_date
                    ),
                    out_fields=["parentglobalid"],
                    return_geometry=False,
                )
                .sdf
            )
            if not sdf.empty:
                dfs.extend(sdf["parentglobalid"].unique())
        recent_surveys = set(dfs)
        globalids = ", ".join([f"'{x}'" for x in recent_surveys])

    q = f"({time_query.format(e=edit_field, start_date=start_date, end_date=end_date)})"
    if globalids:
        q += f"or (globalid in ({globalids}))"

    sdf = layer.query(q, out_fields=["objectid"], return_geometry=False).sdf

    return [] if sdf.empty else sdf["objectid"].to_list()


class Survey123Service:
    def __init__(self, item: gis.Item):
        self.service = item

        self._survey_layer = None
        self._survey_properties = None
        self._related_tables = None

    @property
    def survey_layer(self):
        if self._survey_layer is None:
            self._survey_layer = self.service.layers[0]  # type: ignore
        return self._survey_layer

    @property
    def related_tables(self):
        if self._related_tables is None:
            self._related_tables = get_related_tables(self.service, self.survey_layer)
        return self._related_tables

    def get_recent(self, start_date=None, end_date=None):
        return get_recent(
            self.survey_layer,
            related_tables=self.related_tables,
            start_date=start_date,
            end_date=end_date,
        )

    def get_related_records(self, oid, context_dir):
        return get_related_records(
            self.survey_layer, oid, context_dir, tables=self.related_tables
        )

    def get_contexts(
        self,
        oids,
        context_file_pattern=None,
        download_attachments=True,
        get_relates=True,
    ):
        return get_contexts(
            self.survey_layer,
            oids,
            tables=self.related_tables,
            service=self.service,
            context_file_pattern=context_file_pattern,
            download_attachments=download_attachments,
            get_relates=get_relates,
        )

    def write_contexts(
        self,
        oids,
        context_file_pattern=None,
        download_attachments=True,
        get_relates=True,
    ):
        filepaths = []

        contexts = self.get_contexts(
            oids,
            context_file_pattern=context_file_pattern,
            download_attachments=download_attachments,
            get_relates=get_relates,
        )

        for context in contexts:
            file = write_context(context, context.get("_filepath", None))
            filepaths.append(file)

        return filepaths
