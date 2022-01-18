import json
from pathlib import Path
from typing import List, Optional, Union

import arcgis
import pandas

from agolutils.arcgis.utils import get_content
from agolutils.utils import make_path


def build_survey123_contexts(
    config,
    oids,
    env: Optional[Union[str, Path]] = None,
    context_file_pattern=None,
):

    if context_file_pattern is None and "context_file_pattern" in config:
        context_file_pattern = config["context_file_pattern"]

    obj = get_content(config=config, env=env)
    surveys = Survey123Service(obj)

    context_paths = surveys.write_contexts(
        oids,
        context_file_pattern=context_file_pattern,
    )

    return context_paths


def make_dir(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_context(record, outpath=None):
    if outpath is None:
        outpath = "./context.json"
    out_file = Path(outpath)

    ctx = json.dumps(record, indent=2)
    out_file.write_text(ctx)
    return out_file


def download_attachment(
    layer: arcgis.gis.Layer,
    oid: int,
    attachment_id: int,
    save_path: Optional[str] = "./",
    filename_prefix: Optional[str] = None,
) -> Path:

    layer.attachments.download(
        oid=oid, attachment_id=attachment_id, save_path=save_path
    )
    att = next(
        filter(
            lambda att: att["id"] == attachment_id, layer.attachments.get_list(oid=oid)
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
    layer: arcgis.gis.Layer,
    oid: int,
    save_path: Optional[str] = "./",
) -> List[Path]:

    files = []

    attachments = layer.attachments.get_list(oid=oid)
    name = layer.properties.name + "-"
    for att in attachments:
        attachment_id = att["id"]
        f = download_attachment(
            layer,
            oid=oid,
            attachment_id=attachment_id,
            save_path=save_path,
            filename_prefix=name,
        )

        files.append(f)

    return files


class Survey123Service:
    def __init__(self, item: arcgis.gis.Item):
        self.service = item

        self._survey_layer = None
        self._survey_properties = None
        self._tables = None

    @property
    def survey_layer(self):
        if self._survey_layer is None:
            self._survey_layer = self.service.layers[0]
        return self._survey_layer

    @property
    def survey_properties(self):
        if self._survey_properties is None:
            all_properties = dict(self.survey_layer.properties)
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

            self._survey_properties = {
                k: v for k, v in all_properties.items() if k in keys
            }
        return self._survey_properties

    def get_layer_records(self, oids: List[int]):
        object_ids = ",".join(map(str, oids))
        q = self.survey_layer.query(object_ids=object_ids)
        df = q.sdf
        return json.loads(df.to_json(orient="records"))

    def get_Layer_by_prop(self, prop, equals):
        fxn = lambda x: x.properties.get(prop) == equals
        return next(filter(fxn, self.service.layers + self.service.tables))

    def get_related_records(self, layer, oid, context_dir):

        relates = {}

        for relationship in layer.properties.relationships:

            rel_id = relationship["id"]
            tableid = relationship["relatedTableId"]
            table = self.get_Layer_by_prop("id", tableid)
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

            rel_df = table.query(object_ids=",".join(map(str, rel_oids))).sdf
            files = []
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

            if files:
                rel_df = rel_df.merge(pandas.DataFrame(files), on="objectid")

            relates[name] = json.loads(rel_df.to_json(orient="records"))

        return relates

    def write_contexts(
        self,
        oids,
        context_file_pattern=None,
        download_attachments=True,
        download_relates=True,
    ):

        filepaths = []
        records = self.get_layer_records(oids)
        if context_file_pattern is None:
            context_file_pattern = "contexts/{globalid}.json"

        for record in records:
            context = record
            oid = context["objectid"]
            outpath = make_path(context_file_pattern.format(**context))
            outdir = make_dir(outpath.parent)
            context["__layer_properties"] = self.survey_properties
            context["_layer_name"] = self.survey_properties.get("name", "no-layer-name")

            if download_relates:
                context["relates"] = self.get_related_records(
                    self.survey_layer, oid, context_dir=outdir
                )

            if download_attachments:

                attachments = self.survey_layer.attachments.get_list(oid)
                for att in attachments:
                    file = download_attachment(
                        self.survey_layer,
                        oid=oid,
                        attachment_id=att["id"],
                        save_path=outdir,
                        filename_prefix=self.survey_properties["name"] + "-",
                    )

                    att["attachment_filepath"] = str(file.relative_to(outdir.resolve()))
                context["attachments"] = attachments

            file = write_context(context, outpath)
            filepaths.append(file)

        return filepaths
