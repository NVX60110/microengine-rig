#!/usr/bin/env pvpython
"""Render the fine CFD-01 TDC tracer slice with cell edges for the report."""
from __future__ import annotations

import argparse
from pathlib import Path
from paraview.simple import (  # type: ignore
    ColorBy, GetColorTransferFunction, GetOpacityTransferFunction,
    GetActiveViewOrCreate, OpenFOAMReader, SaveScreenshot, Show, Slice,
    UpdatePipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--time", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    marker = args.case / "cfd01.foam"
    marker.touch(exist_ok=True)
    reader = OpenFOAMReader(FileName=str(marker))
    reader.MeshRegions = ["internalMesh"]
    reader.CellArrays = ["tracer"]
    UpdatePipeline(time=args.time, proxy=reader)
    cut = Slice(Input=reader)
    cut.SliceType.Origin = [0.0, 0.0, 0.004]
    cut.SliceType.Normal = [0.0, 1.0, 0.0]
    UpdatePipeline(time=args.time, proxy=cut)
    view = GetActiveViewOrCreate("RenderView")
    display = Show(cut, view)
    display.Representation = "Surface With Edges"
    ColorBy(display, ("CELLS", "tracer"))
    display.SetScalarBarVisibility(view, True)

    # Overlay the moving piston patch so the screenshot documents both the
    # mesh motion boundary and the passive-scalar field.  A separate reader is
    # used because the internal slice and boundary patch have different data
    # associations in ParaView's OpenFOAM reader.
    piston_reader = OpenFOAMReader(FileName=str(marker))
    piston_reader.MeshRegions = ["patch/piston"]
    piston_reader.CellArrays = []
    UpdatePipeline(time=args.time, proxy=piston_reader)
    piston_display = Show(piston_reader, view)
    piston_display.Representation = "Surface With Edges"
    piston_display.DiffuseColor = [1.0, 0.75, 0.1]
    piston_display.LineWidth = 4.0
    piston_display.Opacity = 0.9
    colour = GetColorTransferFunction("tracer")
    colour.RescaleTransferFunction(0.0, 1.0)
    opacity = GetOpacityTransferFunction("tracer")
    opacity.RescaleTransferFunction(0.0, 1.0)
    view.ViewSize = [1400, 900]
    view.CameraPosition = [0.012, -0.018, 0.006]
    view.CameraFocalPoint = [0.0, 0.0, 0.004]
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.ResetCamera()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(args.output), view)


if __name__ == "__main__":
    main()
