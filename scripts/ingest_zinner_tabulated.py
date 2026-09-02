"""Materialize the verbatim Zinner (2008) Appendix TABULATED DATA rows.

The source PDF is intentionally not committed.  The rows below were transcribed
from its Appendix tables; this script makes the compact CSV deterministic and
keeps the table/page provenance on every row.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "zinner2008" / "shock_tube_tabulated.csv"

# The appendix prints six numeric values per row.  Exactly one of the final
# two correlation columns is populated; LOW_ROWS records which rows are in the
# low-temperature correlation column.
DATA = {
1: (2.0, "80CH4_20DME", 69, """
1487 12.4 39 13.2 1505 32
1384 13.8 84 14.8 1401 82
1338 15.4 128 16.5 1355 127
1276 15.6 235 16.2 1286 291
1195 17.0 477 17.7 1204 825
1123 17.7 915 18.5 1133 948
1074 18.9 1311 19.7 1082 1153
1020 19.1 1754 20.1 1030 1519
993 20.2 1809 21.2 1003 1699
956 20.5 2091 21.7 966 2121
929 21.6 2287 23.1 941 2361
1491 5.4 62 5.4 1493 60
1387 5.9 149 6.2 1401 136
1314 6.3 283 6.7 1329 293
1281 6.9 383 7.2 1293 430
1227 7.2 662 7.8 1243 781
1190 7.5 1049 8.0 1203 1349
1650 0.9 92 1.0 1656 43
1551 1.1 152 1.2 1563 79
1459 1.3 265 1.3 1472 167
1407 1.3 401 1.4 1423 258
1352 1.4 749 1.6 1379 390
1323 1.5 941 1.7 1340 588
"""),
2: (1.0, "80CH4_20DME", 69, """
1347 26.0 80 27.2 1359 95
1299 27.7 130 28.2 1303 180
1212 30.0 296 31.1 1221 495
1119 31.6 598 33.5 1133 666
1040 32.5 985 34.7 1054 980
996 35.2 1180 37.2 1008 1195
1464 6.1 68 6.4 1478 66
1376 6.8 152 7.2 1391 148
1303 7.0 316 7.7 1328 289
1272 7.5 450 7.9 1285 479
1223 7.7 854 8.6 1251 711
1198 8.1 1074 8.9 1222 1021
1587 1.3 48 1.3 1597 60
1517 1.4 85 1.4 1522 107
1403 1.5 262 1.5 1406 314
1336 1.6 579 1.8 1353 517
1240 1.7 1614 1.8 1251 1774
"""),
3: (0.5, "80CH4_20DME", 70, """
1442 15.6 46 15.9 1448 56
1395 16.2 80 16.4 1400 90
1297 17.6 240 18.5 1310 231
1218 18.6 541 19.5 1229 634
1132 19.5 1283 20.8 1149 1662
1050 20.6 2366 22.3 1069 2327
1032 21.4 2719 22.4 1043 2700
1473 6.5 56 6.8 1488 63
1393 7.1 118 7.3 1400 145
1335 7.5 266 8.2 1359 212
1283 7.6 469 8.3 1305 394
1254 8.1 668 9.1 1286 473
1207 8.2 1159 9.1 1236 915
1153 8.4 2133 9.5 1184 1865
1510 1.4 71 1.5 1515 122
1443 1.6 157 1.7 1456 197
1370 1.7 317 1.8 1378 425
1311 1.8 632 1.8 1321 803
1262 1.8 1261 1.8 1267 1541
"""),
4: (0.3, "80CH4_20DME", 70, """
1438 28.2 73 28.4 1440 46
1320 28.0 151 28.8 1329 152
1271 29.5 276 31.0 1286 246
1171 31.2 740 34.4 1198 991
1088 32.6 1532 36.4 1115 1377
1046 34.1 2114 38.5 1076 1596
1433 6.7 64 6.8 1440 108
1400 7.0 126 7.2 1409 144
1325 7.2 293 7.6 1339 301
1307 7.6 391 8.1 1324 341
1234 7.6 949 8.3 1259 760
1214 7.9 1244 8.8 1242 916
1170 8.0 2075 8.9 1200 1635
1546 1.5 59 1.5 1561 86
1452 1.6 132 1.6 1457 213
1397 1.6 263 1.7 1405 354
1322 1.8 783 1.9 1339 672
1278 1.9 1269 2.0 1300 1045
"""),
5: (2.0, "60CH4_40DME", 71, """
1355 14.2 58 14.8 1365 63
1256 16.2 162 16.8 1264 197
1197 18.3 254 18.6 1200 447
1161 18.8 367 19.4 1168 706
1089 17.9 589 19.1 1102 634
958 19.7 875 21.1 970 1269
1077 20.3 885 21.6 1089 589
959 20.6 959 21.5 967 1270
973 20.3 1108 21.4 982 1142
1027 20.6 1142 21.3 1033 827
913 22.0 1474 23.1 922 1627
948 21.7 1928 22.9 957 1254
1443 5.8 40 6.3 1462 38
1360 6.0 87 6.2 1367 104
1314 6.7 158 7.0 1324 157
1258 7.3 267 7.6 1266 308
1208 7.4 483 7.7 1217 593
1165 7.7 753 8.3 1179 981
1517 1.3 83 1.4 1534 49
1456 1.3 117 1.4 1471 85
1348 1.5 371 1.5 1354 276
1298 1.6 507 1.7 1308 445
1239 1.6 1073 1.8 1255 843
1208 1.8 1152 1.8 1210 1555
"""),
6: (1.0, "60CH4_40DME", 71, """
1327 28.0 57 30.1 1346 55
1229 32.2 135 33.6 1239 194
1135 34.1 285 35.3 1143 774
1083 33.9 397 35.5 1093 456
1070 34.9 435 38.6 1092 414
997 30.5 477 32.1 1007 862
1020 29.9 641 35.5 1057 557
989 34.4 679 36.5 1001 763
1424 6.5 42 6.8 1436 51
1356 7.0 108 7.1 1360 110
1283 7.3 235 8.1 1310 182
1220 8.1 493 8.9 1242 415
1174 8.2 882 9.4 1209 631
1135 8.2 1314 9.1 1159 1338
1508 1.5 49 1.5 1520 55
1491 1.4 57 1.5 1502 66
1412 1.6 119 1.6 1413 152
1299 1.7 509 1.7 1310 456
1270 1.8 636 1.9 1279 638
1225 1.8 1295 2.0 1245 971
"""),
7: (0.5, "60CH4_40DME", 72, """
1395 16.0 43 16.9 1411 41
1347 17.1 86 18.0 1361 68
1258 18.5 219 19.5 1273 187
1204 20.0 396 22.1 1231 304
1115 20.3 828 22.4 1139 957
1047 21.0 1474 23.3 1071 1314
1422 6.8 64 7.1 1436 54
1377 7.1 91 7.1 1377 99
1335 7.7 164 8.4 1362 106
1287 7.8 287 8.5 1313 185
1248 8.3 439 9.3 1280 265
1169 8.5 1145 10.0 1208 669
1482 0.8 74 0.8 1488 116
1415 0.9 142 0.9 1425 205
1398 0.9 183 0.9 1411 231
1345 0.9 383 0.9 1357 412
1322 0.9 487 0.9 1325 597
1316 0.8 647 0.8 1319 685
1292 1.0 908 1.0 1297 820
1520 1.6 33 1.7 1532 52
1426 1.6 112 1.7 1439 124
1338 1.8 258 1.8 1340 345
1347 1.8 316 1.8 1353 294
1250 1.8 1004 1.9 1267 795
1241 1.9 1235 2.0 1250 988
"""),
8: (0.3, "60CH4_40DME", 73, """
1414 26.8 36 27.7 1425 29
1384 27.6 46 28.3 1392 40
1285 30.0 153 31.5 1298 110
1209 33.1 304 35.1 1225 270
1120 33.8 683 37.0 1142 708
1052 34.5 1120 38.0 1075 974
1014 35.7 1476 40.0 1041 1119
1422 6.7 57 6.9 1430 63
1380 7.0 80 7.2 1388 94
1347 7.4 130 7.7 1361 122
1297 7.7 278 8.1 1314 203
1262 7.9 436 8.0 1265 378
1262 7.9 453 8.7 1288 269
1223 8.2 717 8.7 1240 501
1168 8.4 1363 9.0 1185 1070
1488 1.6 32 1.6 1488 84
1425 1.6 104 1.6 1430 146
1357 1.8 252 1.8 1363 279
1334 1.9 289 2.0 1344 332
1287 1.9 555 2.0 1299 564
1233 1.9 1283 2.1 1252 999
"""),
}

LOW_ROWS = {
    1: {6, 7, 8, 9, 10, 11},
    2: {4, 5, 6},
    3: {5, 6, 7},
    4: {4, 5, 6},
    5: {5, 6, 7, 8, 9, 10, 11, 12},
    6: {3, 4, 5, 6, 7, 8},
    7: {5, 6},
    8: {5, 6, 7},
}

FIELDS = [
    "record_id", "mixture_number", "mixture_label", "ch4_volume_fraction",
    "dme_volume_fraction", "equivalence_ratio", "temperature_adjusted_K",
    "pressure_adjusted_atm", "ignition_delay_us", "pressure_original_atm",
    "temperature_original_K", "high_temperature_correlation_us",
    "low_temperature_correlation_us", "adjustment_status", "ignition_target",
    "ignition_type", "facility", "source_instrument", "provenance", "notes",
]


def main() -> None:
    # Kept separate from the source transcription above so the generated CSV is
    # reproducible by reviewers; the source rows have six numeric columns and
    # the final correlation is assigned to the printed high/low column.
    rows: list[dict[str, str]] = []
    for mix, (phi, label, page, raw) in DATA.items():
        ch4 = "0.80" if label.startswith("80") else "0.60"
        dme = "0.20" if label.startswith("80") else "0.40"
        for row_number, line in enumerate(raw.strip().splitlines(), 1):
            values = line.split()
            if len(values) != 6:
                raise ValueError(f"bad row Mix #{mix}, row {row_number}: {line}")
            t_adj, p_adj, tau, p_orig, t_orig, correlation = values
            high, low = ("", correlation) if row_number in LOW_ROWS[mix] else (correlation, "")
            rows.append({
                "record_id": f"zinner2008_mix{mix}_row{row_number:02d}",
                "mixture_number": str(mix), "mixture_label": label,
                "ch4_volume_fraction": ch4, "dme_volume_fraction": dme,
                "equivalence_ratio": str(phi), "temperature_adjusted_K": t_adj,
                "pressure_adjusted_atm": p_adj, "ignition_delay_us": tau,
                "pressure_original_atm": p_orig, "temperature_original_K": t_orig,
                "high_temperature_correlation_us": high,
                "low_temperature_correlation_us": low,
                "adjustment_status": "adjusted_state_not_delay",
                "ignition_target": "endwall pressure rise",
                "ignition_type": "total ignition delay (tau_ign)",
                "facility": "not_stated_per_appendix_row",
                "source_instrument": "endwall piezoelectric pressure transducer",
                "provenance": (f"Zinner 2008 Appendix TABULATED DATA, Mix #{mix}, "
                               f"printed p.{page - 14}, PDF p.{page}, row {row_number}"),
                "notes": ("Adjusted T/P are the thesis adjusted state; original P/T and "
                          "both thesis correlation columns are retained verbatim. Facility "
                          "is not assigned because the appendix table does not label rows."),
            })
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
