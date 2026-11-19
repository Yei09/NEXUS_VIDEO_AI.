# NEXUS VIDEO AI - Windows 11 read-only hardware diagnostic
# Compatible with Windows PowerShell 5.1 and PowerShell 7.
# Local CIM/WMI queries and version probes only.
# No downloads, installations, settings changes, registry/environment writes,
# servers, or network requests.

$ErrorActionPreference = "Stop"

function Get-LocalToolStatus {
    param([string]$Name, [string[]]$Arguments = @("--version"))
    $command = Get-Command -Name $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) {
        return [ordered]@{ name=$Name; installed=$false; path=$null; version=$null; note="No se encontró un ejecutable en PATH." }
    }
    $exePath = $command.Source
    if (-not $exePath) { $exePath = $command.Definition }
    if ($exePath -match '\\Microsoft\\WindowsApps\\') {
        return [ordered]@{ name=$Name; installed=$false; path=$exePath; version=$null; note="Alias de WindowsApps detectado; no se ejecutó." }
    }
    try {
        $lines = @(& $exePath @Arguments 2>&1 | Select-Object -First 3)
        $versionText = ($lines | ForEach-Object { "$_" }) -join " "
        return [ordered]@{ name=$Name; installed=$true; path=$exePath; version=$versionText.Trim(); note="Solo se consultó la versión." }
    } catch {
        return [ordered]@{ name=$Name; installed=$true; path=$exePath; version=$null; note="No se pudo consultar la versión: $($_.Exception.Message)" }
    }
}

$cpu = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1 Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed, AddressWidth, Architecture
$computer = Get-CimInstance -ClassName Win32_ComputerSystem
$os = Get-CimInstance -ClassName Win32_OperatingSystem

$pageFiles = @()
try { $pageFiles = @(Get-CimInstance -ClassName Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage) } catch { $pageFiles = @() }
$pageFileSettings = @()
try { $pageFileSettings = @(Get-CimInstance -ClassName Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize) } catch { $pageFileSettings = @() }

$gpus = @(Get-CimInstance -ClassName Win32_VideoController | ForEach-Object {
    [ordered]@{
        name=$_.Name
        adapter_ram_bytes_reported_by_wmi=$_.AdapterRAM
        adapter_ram_gb_reported_by_wmi=if ($_.AdapterRAM) { [math]::Round(([double]$_.AdapterRAM / 1GB),2) } else { $null }
        driver_version=$_.DriverVersion
        video_processor=$_.VideoProcessor
        video_mode=$_.VideoModeDescription
        pnp_device_id=$_.PNPDeviceID
        note="AdapterRAM puede estar limitado y no representa necesariamente la memoria compartida dinámica de una iGPU."
    }
})

$gpuMemoryCounters = @()
try {
    $gpuMemoryCounters = @(Get-CimInstance -Namespace "root/cimv2" -ClassName "Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory" | ForEach-Object {
        $item=[ordered]@{}
        foreach ($property in $_.CimInstanceProperties) {
            if ($property.Name -notlike "__*") { $item[$property.Name]=$property.Value }
        }
        $item
    })
} catch { $gpuMemoryCounters = @() }

$disks = @(Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    [ordered]@{
        device_id=$_.DeviceID
        volume_name=$_.VolumeName
        file_system=$_.FileSystem
        size_gb=if ($_.Size) { [math]::Round(([double]$_.Size / 1GB),2) } else { $null }
        free_gb=if ($_.FreeSpace) { [math]::Round(([double]$_.FreeSpace / 1GB),2) } else { $null }
    }
})

$result = [ordered]@{
    diagnostic=[ordered]@{
        name="NEXUS VIDEO AI - Local hardware diagnostic"
        schema_version="1.0"
        timestamp_local=(Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
        execution_scope="Este equipo Windows; no es una medición del runner de GitHub."
        read_only=$true
        network_requests=$false
        downloads=$false
        installations=$false
        registry_changes=$false
        environment_variable_changes=$false
        server_start=$false
        administrator_required=$false
    }
    operating_system=[ordered]@{
        caption=$os.Caption
        version=$os.Version
        build_number=$os.BuildNumber
        architecture=$os.OSArchitecture
        system_drive=$os.SystemDrive
        last_boot_up_time=$os.LastBootUpTime
    }
    processor=[ordered]@{
        model=$cpu.Name
        manufacturer=$cpu.Manufacturer
        physical_cores=$cpu.NumberOfCores
        logical_processors=$cpu.NumberOfLogicalProcessors
        max_clock_mhz=$cpu.MaxClockSpeed
        current_clock_mhz=$cpu.CurrentClockSpeed
        reported_address_width_bits=$cpu.AddressWidth
        wmi_architecture_code=$cpu.Architecture
    }
    memory=[ordered]@{
        physical_total_gb=[math]::Round(([double]$computer.TotalPhysicalMemory / 1GB),2)
        physical_available_gb=[math]::Round(([double]$os.FreePhysicalMemory * 1KB / 1GB),2)
        virtual_total_gb=[math]::Round(([double]$os.TotalVirtualMemorySize * 1KB / 1GB),2)
        virtual_available_gb=[math]::Round(([double]$os.FreeVirtualMemory * 1KB / 1GB),2)
        pagefile_usage=$pageFiles
        pagefile_settings=$pageFileSettings
        note="La memoria compartida de la GPU forma parte de la RAM física; no debe sumarse dos veces."
    }
    graphics=[ordered]@{
        adapters=$gpus
        memory_counters_if_supported=$gpuMemoryCounters
        note="La memoria de Radeon integrada es dinámica y compartida. Si Windows no publica el presupuesto disponible, se deja vacío; no se inventa."
    }
    storage=$disks
    tools=[ordered]@{
        python=(Get-LocalToolStatus -Name "python" -Arguments @("--version"))
        python_launcher=(Get-LocalToolStatus -Name "py" -Arguments @("--version"))
        ffmpeg=(Get-LocalToolStatus -Name "ffmpeg" -Arguments @("-version"))
        blender=(Get-LocalToolStatus -Name "blender" -Arguments @("--version"))
    }
    security=[ordered]@{
        network="No se invocan clientes HTTP, APIs ni servicios remotos."
        file_writes="El script no crea ni modifica archivos. La redirección opcional de salida a JSON la realiza el comando externo elegido por el usuario."
        registry="No se escriben claves ni valores."
        environment="No se establecen ni modifican variables de entorno."
        installation="No se invocan winget, choco, pip, npm ni instaladores."
        processes="Solo se consulta la versión de ejecutables locales Python, FFmpeg y Blender si están en PATH."
    }
}
$result | ConvertTo-Json -Depth 8
