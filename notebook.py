import marimo

__generated_with = "0.14.6"
app = marimo.App(width="medium")


@app.cell
def _():
    from json import dumps, load

    import plotly.graph_objects as go
    import polars as pl

    def pprint_dict(obj: dict):
        print(dumps(obj, indent=2))
    return go, load, pl, pprint_dict


@app.cell
def _(load, pprint_dict):
    from os import getenv
    from pathlib import Path

    def check_file_exist(file_to_check: Path, description: str) -> Path:
        if file_to_check.exists():
            print(f"✅ Le fichier de {description} '{file_to_check}' existe bien.")
        else:
            print(f"❌ Le fichier de {description} '{file_to_check}' n'existe pas ou est mal nommé.")
        return file_to_check

    _BENCHMARK_SOURCES_CONFIG_FILE = check_file_exist(
        Path(getenv("BENCHMARK_SOURCES_CONFIG_FILE")),
        "configuration de l'analyse",
    )

    with open(_BENCHMARK_SOURCES_CONFIG_FILE, encoding="utf-8") as config_file:
        _analysis_config = load(config_file)

        _BUILD_RESULTS_DIR = Path(_analysis_config["build_results_dir"])
        BUILD_TIMES_FILE = check_file_exist(_BUILD_RESULTS_DIR / _analysis_config["build_times"], "temps de construction des images")
        _BENCHMARK_RESULTS_DIR = Path(_analysis_config["benchmark_results_dir"])
        CPU_USAGE_FILE = check_file_exist(_BENCHMARK_RESULTS_DIR / _analysis_config["cpu_usage"], "consommation CPU")
        RAM_USAGE_FILE = check_file_exist(_BENCHMARK_RESULTS_DIR / _analysis_config["ram_usage"], "consommation RAM")

        IMAGE_NAMES = tuple(_analysis_config["images"].keys())
        COLORS_BY_IMAGE: dict[str, str] = {
            image_name: image_dict["color"]
            for image_name, image_dict in _analysis_config["images"].items()
        }
        RESULTS_BY_IMAGE: dict[str, Path] = {
            image_name: check_file_exist(_BENCHMARK_RESULTS_DIR / f"{image_dict['results_prefix']}_{image_name}.json", f"résultats pour l'image {image_name}")
            for image_name, image_dict in _analysis_config["images"].items()
        }
        pprint_dict(_analysis_config)

    return (
        BUILD_TIMES_FILE,
        COLORS_BY_IMAGE,
        CPU_USAGE_FILE,
        IMAGE_NAMES,
        Path,
        RAM_USAGE_FILE,
        RESULTS_BY_IMAGE,
    )


@app.cell
def _(BUILD_TIMES_FILE, COLORS_BY_IMAGE: dict[str, str], Path, pprint_dict):
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

    def scrap_images_build_time_and_size(build_times_path: Path, colors_by_image: dict[str, str]) -> dict:
        stats_by_image = {}
        with open(build_times_path, encoding="utf-8") as build_times_file:
            while (file_line := next(build_times_file, None)) is not None:
                image_name_match = IMAGE_START_PATTERN.search(file_line)
                if image_name_match:
                    image_name = image_name_match.group(1)
                    stats_by_image[image_name] = {
                        "color": colors_by_image[image_name]
                    } | scrap_image_build_time_and_size(build_times_file)

        return stats_by_image

    stats_by_image = scrap_images_build_time_and_size(BUILD_TIMES_FILE, COLORS_BY_IMAGE)
    pprint_dict(stats_by_image)
    return (stats_by_image,)


@app.cell
def _(
    COLORS_BY_IMAGE: dict[str, str],
    CPU_USAGE_FILE,
    IMAGE_NAMES,
    Path,
    RAM_USAGE_FILE,
    RESULTS_BY_IMAGE: "dict[str, Path]",
    go,
    load,
    pl,
    pprint_dict,
    stats_by_image,
):
    # affichage des consommations CPU et RAM

    from polars import DataFrame, read_csv, from_epoch
    from polars.datatypes.classes import Float64, Int64

    benchmark_image_columns = {
        "Time": "Time",
        "bench_pyenvbasic": "pyenvbasic",
        "bench_pyenvoptmarch": "pyenvoptmarch",
        "bench_official": "official",
        "bench_debian": "debian",
        "bench_pyenvoptmarchbolt": "pyenvoptmarchbolt",
        "bench_pyenvopt": "pyenvopt",
        "bench_uv": "uv",
    }

    def load_dataframe(data_file: Path, values_datatype) -> DataFrame:
        # https://docs.pola.rs/api/python/stable/reference/api/polars.read_csv.html
        return read_csv(
            data_file,
            # sélection et renommage des colonnes
            columns=list(benchmark_image_columns.keys()),
            new_columns=list(benchmark_image_columns.values()),
            null_values="undefined",
            infer_schema=False,
            schema_overrides={"Time": Int64} | {
                benchmark_image_column: values_datatype
                for benchmark_image_column in benchmark_image_columns
            }
        ).with_columns(from_epoch("Time", time_unit="ms"))


    cpu_df = load_dataframe(CPU_USAGE_FILE, Float64)
    ram_df = load_dataframe(RAM_USAGE_FILE, Int64)

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

    def narrow_cpu_df(values_df: DataFrame, image_names: list[str]) -> tuple[DataFrame, dict]:
        narrowed_df = values_df.select(values_df.columns).with_columns(
            **{
                image_column: pl.when(
                    pl.col(image_column).diff(n=1).abs() > 0.4
                ).then(None).otherwise(pl.col(image_column))
                for image_column in values_df.columns
                if image_column != "Time"
            }
        )

        return narrowed_df, {
            image_name: cpu_mean_values[0]
            for image_name, cpu_mean_values in narrowed_df.select(image_names).mean().to_dict(as_series=False).items()
        }

    narrowed_cpu_df, cpu_mean_by_image = narrow_cpu_df(cpu_df, IMAGE_NAMES)
    # pprint_dict(cpu_mean_by_image)

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

    ram_mean_by_image = {
        image_name: ram_mean_values[0]
        for image_name, ram_mean_values in narrowed_ram_df.select(COLORS_BY_IMAGE.keys()).mean().to_dict(as_series=False).items()
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
    # chargement des performances métier
    def load_business_perfs(result_files_by_image: dict[str, Path], image_stats: dict):
        for image_name, result_path in result_files_by_image.items():
            with open(result_path, encoding="utf-8") as result_file:
                image_results = load(result_file)
                tasks_nb = image_results["tasks"]
                image_stats[image_name] |= {
                    "tasks_per_min": {
                        "value": image_results["tasks_per_min"],
                        "unit": "t",
                    },
                    "cpu_per_task": {
                        "value": image_stats[image_name]["cpu_mean"]["value"] / tasks_nb,
                        "unit": "%",
                    },
                    "ram_per_task": {
                        "value": image_stats[image_name]["ram_mean"]["value"] / tasks_nb,
                        "unit": "Mo",
                    },
                }

    load_business_perfs(RESULTS_BY_IMAGE, stats_by_image)
    pprint_dict(stats_by_image)

    return cpu_df, narrowed_cpu_df, narrowed_ram_df, plot_timeseries, ram_df


@app.cell
def _(
    COLORS_BY_IMAGE: dict[str, str],
    cpu_df,
    narrowed_cpu_df,
    narrowed_ram_df,
    plot_timeseries,
    ram_df,
):
    plot_timeseries(cpu_df, COLORS_BY_IMAGE, "Évolution des consommations CPU des différentes images")
    plot_timeseries(narrowed_cpu_df, COLORS_BY_IMAGE, "Évolution des CPU des différentes images sans les rampes")

    plot_timeseries(ram_df, COLORS_BY_IMAGE, "Évolution des consommations RAM des différentes images")
    plot_timeseries(narrowed_ram_df, COLORS_BY_IMAGE, "Évolution des RAM des différentes images sans les rampes")

    return


@app.cell
def _(go, stats_by_image):
    categories = {
        "build_duration": "temps de build",
        "build_size": "taille de l'image",
        # "cpu_mean": "CPU moyen",
        # "ram_mean": "RAM moyenne",
        "tasks_per_min": "tâches / minute",
        "cpu_per_task" : "CPU / tâche",
        "ram_per_task": "RAM / tâche",
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
