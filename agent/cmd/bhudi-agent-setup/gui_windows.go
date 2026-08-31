//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// runInstallerGUI launches a native Windows Forms wizard through the Windows
// PowerShell runtime. The setup executable itself is built with -H=windowsgui,
// so no console window is shown to the customer.
func runInstallerGUI() {
	script := `$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object Windows.Forms.Form
$form.Text = 'Bhudi Agent Setup'
$form.StartPosition = 'CenterScreen'
$form.Size = New-Object Drawing.Size(620,400)
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$title = New-Object Windows.Forms.Label
$title.Text = 'Bhudi Agent Setup'
$title.Font = New-Object Drawing.Font('Segoe UI',18,[Drawing.FontStyle]::Bold)
$title.Location = New-Object Drawing.Point(30,25)
$title.AutoSize = $true
$form.Controls.Add($title)

$body = New-Object Windows.Forms.Label
$body.Text = 'Welcome to the Bhudi Agent Setup Wizard.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'This wizard installs and enrolls the Bhudi endpoint agent, registers the Windows service, and installs the Bhudi Support Client.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'Click Next to continue.'
$body.Font = New-Object Drawing.Font('Segoe UI',10)
$body.Location = New-Object Drawing.Point(30,80)
$body.Size = New-Object Drawing.Size(540,170)
$form.Controls.Add($body)

$status = New-Object Windows.Forms.Label
$status.Text = ''
$status.Font = New-Object Drawing.Font('Segoe UI',9)
$status.Location = New-Object Drawing.Point(30,255)
$status.Size = New-Object Drawing.Size(540,30)
$form.Controls.Add($status)

$progress = New-Object Windows.Forms.ProgressBar
$progress.Location = New-Object Drawing.Point(30,290)
$progress.Size = New-Object Drawing.Size(540,20)
$progress.Style = 'Continuous'
$progress.Minimum = 0
$progress.Maximum = 100
$progress.Value = 0
$form.Controls.Add($progress)

$back = New-Object Windows.Forms.Button
$back.Text = '< Back'
$back.Location = New-Object Drawing.Point(300,325)
$back.Size = New-Object Drawing.Size(85,28)
$back.Enabled = $false
$form.Controls.Add($back)

$next = New-Object Windows.Forms.Button
$next.Text = 'Next >'
$next.Location = New-Object Drawing.Point(395,325)
$next.Size = New-Object Drawing.Size(85,28)
$form.Controls.Add($next)

$cancel = New-Object Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.Location = New-Object Drawing.Point(490,325)
$cancel.Size = New-Object Drawing.Size(80,28)
$form.Controls.Add($cancel)

$page = 0
$worker = $null

$cancel.Add_Click({ $form.Close() })
$back.Add_Click({
    if ($page -eq 1) {
        $page = 0
        $body.Text = 'Welcome to the Bhudi Agent Setup Wizard.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'This wizard installs and enrolls the Bhudi endpoint agent, registers the Windows service, and installs the Bhudi Support Client.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'Click Next to continue.'
        $back.Enabled = $false
        $next.Text = 'Next >'
        $status.Text = ''
        $progress.Value = 0
    }
})

$next.Add_Click({
    if ($page -eq 0) {
        $page = 1
        $body.Text = 'The installer is ready to install the Bhudi Agent on this computer.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'The customer enrollment payload embedded in this installer will be used. No credentials will be displayed.'
        $back.Enabled = $true
        $next.Text = 'Install'
        return
    }

    if ($page -eq 1) {
        $page = 2
        $back.Enabled = $false
        $cancel.Enabled = $false
        $next.Enabled = $false
        $next.Text = 'Installing...'
        $body.Text = 'Installing Bhudi Agent...' + [Environment]::NewLine + '' + [Environment]::NewLine + 'Please wait while the endpoint is enrolled and the Windows service is registered.'
        $status.Text = 'Preparing installation...'
        $progress.Style = 'Marquee'
        $progress.MarqueeAnimationSpeed = 25

        $log = Join-Path $env:TEMP ('bhudi-setup-' + [guid]::NewGuid().ToString() + '.log')
        $psi = New-Object Diagnostics.ProcessStartInfo
        $psi.FileName = $env:BHUDI_SETUP_EXE
        $psi.Arguments = 'install-worker'
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.RedirectStandardInput = $false
        $worker = New-Object Diagnostics.Process
        $worker.StartInfo = $psi
        [void]$worker.Start()

        $timer = New-Object Windows.Forms.Timer
        $timer.Interval = 400
        $timer.Add_Tick({
            if ($worker.HasExited) {
                $timer.Stop()
                $progress.Style = 'Continuous'
                $progress.MarqueeAnimationSpeed = 0
                $out = $worker.StandardOutput.ReadToEnd()
                $err = $worker.StandardError.ReadToEnd()
                if ($worker.ExitCode -eq 0) {
                    $progress.Value = 100
                    $status.Text = 'Installation completed successfully.'
                    $body.Text = 'Bhudi Agent Setup completed successfully.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'The Bhudi Agent is enrolled and the Windows service has been installed. The agent will start automatically with Windows.'
                    $next.Text = 'Finish'
                    $next.Enabled = $true
                    $cancel.Enabled = $false
                    $next.Tag = 'finish'
                } else {
                    $status.Text = 'Installation failed.'
                    $body.Text = 'Bhudi Agent Setup could not complete the installation.' + [Environment]::NewLine + '' + [Environment]::NewLine + 'Please contact your administrator and provide the installer log if requested.'
                    $next.Text = 'Close'
                    $next.Enabled = $true
                    $cancel.Enabled = $false
                    $next.Tag = 'fail'
                    [IO.File]::WriteAllText($log, $out + "' + [Environment]::NewLine + '" + $err)
                }
            }
        })
        $timer.Start()
    }
})

$form.Add_Shown({ $form.Activate() })
$next.Add_Click({
    if ($next.Tag -eq 'finish' -or $next.Tag -eq 'fail') { $form.Close() }
})

[void]$form.ShowDialog()
`

	tmp := filepath.Join(os.TempDir(), fmt.Sprintf("bhudi-installer-%d.ps1", os.Getpid()))
	if err := os.WriteFile(tmp, []byte(script), 0600); err != nil {
		return
	}
	defer os.Remove(tmp)

	exe, err := os.Executable()
	if err != nil {
		return
	}
	cmd := exec.Command("powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", tmp)
	cmd.Env = append(os.Environ(), "BHUDI_SETUP_EXE="+exe)
	_ = cmd.Run()
}
