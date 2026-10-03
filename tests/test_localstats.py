from cam_proxy_pi_display import localstats


def _sys(tmp_path, sensors):
    for i, (name, temp) in enumerate(sensors):
        d = tmp_path / "class" / "hwmon" / f"hwmon{i}"
        d.mkdir(parents=True)
        (d / "name").write_text(name + "\n")
        if temp is not None:
            (d / "temp1_input").write_text(f"{temp}\n")
    return tmp_path


def test_cpu_temp_finds_cpu_thermal(tmp_path):
    sys = _sys(tmp_path, [("rpi_volt", None), ("cpu_thermal", 53612)])
    assert localstats.cpu_temp(sys) == 53.6


def test_cpu_temp_missing(tmp_path):
    assert localstats.cpu_temp(tmp_path) is None
    sys = _sys(tmp_path, [("other", 1000)])
    assert localstats.cpu_temp(sys) is None


def test_uptime(tmp_path):
    (tmp_path / "uptime").write_text("412233.71 1612345.10\n")
    assert localstats.uptime(tmp_path) == 412233
    assert localstats.uptime(tmp_path / "nope") is None


def test_model(tmp_path):
    (tmp_path / "cpuinfo").write_text(
        "processor\t: 0\n\nRevision\t: d03115\nModel\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
    )
    assert localstats.model(tmp_path) == "Raspberry Pi 4 Model B Rev 1.5"
    (tmp_path / "cpuinfo").write_text("processor : 0\n")
    assert localstats.model(tmp_path) is None


def test_default_interface(tmp_path):
    (tmp_path / "net").mkdir()
    (tmp_path / "net" / "route").write_text(
        "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
        "wlan0\t00000000\t010200C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n"
        "eth0\t00000000\t010200C0\t0003\t0\t0\t100\t00000000\t0\t0\t0\n"
        "eth0\t000200C0\t00000000\t0001\t0\t0\t100\t00FFFFFF\t0\t0\t0\n"
    )
    assert localstats.default_interface(tmp_path) == "eth0"
    assert localstats.default_interface(tmp_path / "nope") is None


def test_disk_of_root():
    d = localstats.disk("/")
    assert d is not None
    assert 0 <= d["usedPercent"] <= 100
    assert d["sizeBytes"] > 0
    assert localstats.disk("/does/not/exist") is None


def test_read_has_all_keys(tmp_path):
    r = localstats.read(proc=tmp_path, sys=tmp_path, disk_path="/")
    assert set(r) == {"disk", "cpuTempC", "uptimeS", "model", "ip"}
    assert r["cpuTempC"] is None and r["uptimeS"] is None and r["ip"] is None
