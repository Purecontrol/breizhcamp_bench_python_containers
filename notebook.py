import marimo

__generated_with = "0.14.6"
app = marimo.App(width="medium")


@app.cell
def _():
    from json import dumps

    import marimo as mo
    import plotly.graph_objects as go
    import polars as pl

    def pprint_dict(obj: dict):
        print(dumps(obj, indent=2))
    return go, pl, pprint_dict


@app.cell
def _(pprint_dict):
    from json import load
    from os import getenv
    BENCHMARK_SOURCES_CONFIG_FILE = getenv("BENCHMARK_SOURCES_CONFIG_FILE")
    with open(BENCHMARK_SOURCES_CONFIG_FILE, encoding="utf-8") as config_file:
        analysis_config = load(config_file)
        pprint_dict(analysis_config)
    return (analysis_config,)


@app.cell
def _(analysis_config):
    from re import compile as re_compile, Pattern

    # récupération du temps de compilation et de la taille de chaque image

    # "= [2025-06-22_135820] Construction de l'image official"
    IMAGE_START_PATTERN: Pattern = re_compile(r"^= \[(?:[^]]+)\] Construction de l'image (.*)$")
    # "real	0m8,988s"
    IMAGE_BUILD_DURATION_PATTERN: Pattern = re_compile(r"^real\s+((\d+)m([\d,]+)s)$")
    # "breizhcamp_bench_python_containers-official   latest    00bd4c310672   1 second ago   124MB"
    IMAGE_SIZE_PATTERN: Pattern = re_compile(r"^(?:[^\s]+)\s+(?:[^\s]+)\s+(?:[^\s]+)\s+(?:.*)ago\s+((\d+)(\w+))$")

    def scrap_image_build_time_and_size(build_time_file):
        build_stats = {}
        while (file_line := next(build_time_file, None)) is not None:
            build_duration_match = IMAGE_BUILD_DURATION_PATTERN.search(file_line)
            if build_duration_match:
                build_stats["build_duration"] = {
                    "raw": build_duration_match.group(1),
                    "value": (60. * float(build_duration_match.group(2))) + float(build_duration_match.group(3).replace(",", ".")),
                    "unit": "s",
                }
                while (file_line := next(build_time_file, None)) is not None:
                    size_match = IMAGE_SIZE_PATTERN.search(file_line)
                    if size_match:
                        build_stats["build_size"] = {
                            "raw": size_match.group(1),
                            "value": int(size_match.group(2)),
                            "unit": size_match.group(3),
                        }
                        return build_stats

    def scrap_images_build_time_and_size(analysis_config: dict) -> dict:
        stats_by_image = {}
        with open(analysis_config["build_times"], encoding="utf-8") as build_time_file:
            while (file_line := next(build_time_file, None)) is not None:
                image_name_match = IMAGE_START_PATTERN.search(file_line)
                if image_name_match:
                    image_name = image_name_match.group(1)
                    stats_by_image[image_name] = {
                        "color": analysis_config["colors"][image_name]
                    } | scrap_image_build_time_and_size(build_time_file)

        return stats_by_image

    stats_by_image = scrap_images_build_time_and_size(analysis_config)
    # pprint_dict(stats_by_image)
    return (stats_by_image,)


@app.cell
def _(analysis_config, go, pl, stats_by_image):
    # affichage des consommations CPU et RAM

    from polars import DataFrame, read_csv, from_epoch
    from polars.datatypes.classes import Float64, Int64

    benchmark_image_columns = [f"bench_{image}" for image in analysis_config["colors"]]

    def load_dataframe(data_file: str, values_datatype) -> DataFrame:
        # https://docs.pola.rs/api/python/stable/reference/api/polars.read_csv.html
        return read_csv(
            data_file,
            # sélection et renommage des colonnes
            columns=["Time", *benchmark_image_columns],
            new_columns=["Time", *analysis_config["colors"]],
            null_values="undefined",
            infer_schema=False,
            schema_overrides={"Time": Int64} | {
                benchmark_image_column: values_datatype
                for benchmark_image_column in benchmark_image_columns
            }
        ).with_columns(from_epoch("Time", time_unit="ms"))

    cpu_df = load_dataframe(analysis_config["cpu_usage"], Float64)
    ram_df = load_dataframe(analysis_config["ram_usage"], Int64)

    def plot_timeseries(df: DataFrame, colors_by_image: dict, title: str=""):
        image_timeseries = [
            go.Scatter(
                x=df["Time"],
                y=df[image_name],
                line_color=image_color,
                name=image_name
            )
            for image_name, image_color in colors_by_image.items()
            if image_name in df.columns
        ]
        fig = go.Figure(image_timeseries)
        fig.update_layout(title=title, showlegend=True)
        fig.show()

    def narrow_cpu_df(values_df: DataFrame, colors_by_image: dict) -> tuple[DataFrame, dict]:
        narrowed_df = values_df.select(values_df.columns).with_columns(
            **{
                image_column: pl.when(
                    pl.col(image_column).diff(n=1).abs() > 0.2
                ).then(None).otherwise(pl.col(image_column))
                for image_column in values_df.columns
                if image_column != "Time"
            }
        )

        return narrowed_df, {
            image_name: cpu_mean_values[0]
            for image_name, cpu_mean_values in narrowed_df.select(colors_by_image.keys()).mean().to_dict(as_series=False).items()
        }

    narrowed_cpu_df, cpu_mean_by_image = narrow_cpu_df(cpu_df, analysis_config["colors"])
    # pprint_dict(cpu_mean_by_image)
    plot_timeseries(cpu_df, analysis_config["colors"], "Évolution des consommations CPU des différentes images")
    plot_timeseries(narrowed_cpu_df, analysis_config["colors"], "Évolution des CPU des différentes images sans les rampes")

    def narrow_ram_df(values_df: DataFrame, nullifier_df: DataFrame) -> DataFrame:
        return pl.concat(
            [values_df, nullifier_df.clone().rename({
                image_column: f"cpu_{image_column}"
                for image_column in nullifier_df.columns
                if image_column != "Time"
            })],
            how="align_left"
        ).with_columns(
            **{
                image_column: pl.when(
                    pl.col(f"cpu_{image_column}").is_null()
                ).then(None).otherwise(pl.col(image_column))
                for image_column in values_df.columns
                if image_column != "Time"
            }
        ).select(values_df.columns)

    narrowed_ram_df = narrow_ram_df(ram_df, narrowed_cpu_df)

    plot_timeseries(ram_df, analysis_config["colors"], "Évolution des consommations RAM des différentes images")
    plot_timeseries(narrowed_ram_df, analysis_config["colors"], "Évolution des RAM des différentes images sans les rampes")

    ram_mean_by_image = {
        image_name: ram_mean_values[0]
        for image_name, ram_mean_values in narrowed_ram_df.select(analysis_config["colors"].keys()).mean().to_dict(as_series=False).items()
    }
    # pprint_dict(ram_mean_by_image)

    for image_name, cpu_mean in cpu_mean_by_image.items():
        stats_by_image[image_name]["cpu_mean"] = {
            "value": cpu_mean,
            "unit": "%"
        }
    for image_name, ram_mean in ram_mean_by_image.items():
        stats_by_image[image_name]["ram_mean"] = {
            "value": ram_mean / (1024**2),
            "unit": "Mo"
        }

    # pprint_dict(stats_by_image)

    return


@app.cell
def _(go, stats_by_image):
    categories = {
        "build_duration": "temps de build",
        "build_size": "taille de l'image",
        "cpu_mean": "CPU moyen",
        "ram_mean": "RAM moyenne",
    }

    def draw_radar_plot(categories: dict, stats_by_image: dict):
        cyclic_category_codes = [
            *categories.keys(),
            list(categories.keys())[0]
        ]
        cyclic_category_labels = [
            f"{category} (%)"
            for category in [*categories.values(), list(categories.values())[0]]
        ]

        max_value_by_category = {
            category_code: max(
                image_stats[category_code]["value"]
                for image_stats in stats_by_image.values()
            )
            for category_code in categories
        }

        fig = go.Figure()
        for image_name, image_stats in stats_by_image.items():
            fig.add_trace(
                go.Scatterpolar(
                    r=[
                        100 * (image_stats[category_code]["value"] / max_value_by_category[category_code])
                        for category_code in cyclic_category_codes
                    ],
                    text=[
                        f"{image_stats[category_code]['value']}{image_stats[category_code]['unit']}"
                        for category_code in cyclic_category_codes
                    ],
                    line_color=image_stats["color"],
                    theta=cyclic_category_labels,
                    name=image_name,
                )
            )

        fig.update_layout(
            title="Comparaison des performances des images et de leur exécution",
            polar={
                "radialaxis":{
                    "visible": True,
                    "range": [0, 100],
                }
            },
            showlegend=True,
        )

        fig.show()

    draw_radar_plot(categories, stats_by_image)
    return


if __name__ == "__main__":
    app.run()
