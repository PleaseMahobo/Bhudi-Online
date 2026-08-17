//go:build !windows

package main

import (
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "runtime"
    "strings"
)

const systemdUnitName="bhudi-agent.service"

func installService(server,enrollmentToken string)error{server=strings.TrimRight(server,"/");if strings.TrimSpace(enrollmentToken)==""{return fmt.Errorf("customer enrollment token is required")};exe,err:=os.Executable();if err!=nil{return err};exe,_=filepath.Abs(exe);var dest string;if runtime.GOOS=="darwin"{home,_:=os.UserHomeDir();destDir:=filepath.Join(home,"Library","Application Support","Bhudi","Agent");_ = os.MkdirAll(destDir,0755);dest=filepath.Join(destDir,"bhudi-agent")}else{destDir:="/opt/bhudi/agent";if os.Geteuid()!=0{home,_:=os.UserHomeDir();destDir=filepath.Join(home,".local","share","bhudi","agent")};if err:=os.MkdirAll(destDir,0755);err!=nil{return err};dest=filepath.Join(destDir,"bhudi-agent")};if err:=copyFile(exe,dest);err!=nil{return fmt.Errorf("install binary: %w",err)};_ = os.MkdirAll(dataDir(),0755);if err:=os.WriteFile(enrollmentTokenPath(),[]byte(strings.TrimSpace(enrollmentToken)),0600);err!=nil{return err};_=writeConfig(server);switch runtime.GOOS{case "linux":return installSystemd(dest,server);case "darwin":return installLaunchd(dest,server);default:cmd:=exec.Command(dest,"run","-server",server);_=cmd.Start();return nil}}

func uninstallService()error{switch runtime.GOOS{case "linux":_=exec.Command("systemctl","--user","disable","--now",systemdUnitName).Run();_=exec.Command("systemctl","disable","--now",systemdUnitName).Run();home,_:=os.UserHomeDir();_=os.Remove(filepath.Join(home,".config/systemd/user",systemdUnitName));_=os.Remove(filepath.Join("/etc/systemd/system",systemdUnitName));_=exec.Command("systemctl","daemon-reload").Run();case "darwin":plist:=launchdPlistPath();_=exec.Command("launchctl","unload",plist).Run();_=os.Remove(plist)};_=os.Remove(identityPath());_=os.Remove(enrollmentTokenPath());fmt.Println("Uninstall complete.");return nil}

func installSystemd(dest,server string)error{unit:=fmt.Sprintf(`[Unit]\nDescription=Bhudi RMM Agent\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nExecStart=%s run -server %s\nRestart=always\nRestartSec=5\nTimeoutStopSec=20\nKillMode=process\nEnvironment=BHUDI_SERVER_URL=%s\n\n[Install]\nWantedBy=multi-user.target\n`,dest,server,server);if os.Geteuid()==0{path:=filepath.Join("/etc/systemd/system",systemdUnitName);if err:=os.WriteFile(path,[]byte(unit),0644);err!=nil{return err};_=exec.Command("systemctl","daemon-reload").Run();out,err:=exec.Command("systemctl","enable","--now",systemdUnitName).CombinedOutput();if err!=nil{return fmt.Errorf("systemd: %s",strings.TrimSpace(string(out)))};fmt.Println("Bhudi Agent installed (native — no Python required).",path);return nil};home,_:=os.UserHomeDir();dir:=filepath.Join(home,".config/systemd/user");_=os.MkdirAll(dir,0755);path:=filepath.Join(dir,systemdUnitName);userUnit:=fmt.Sprintf(`[Unit]\nDescription=Bhudi RMM Agent\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nExecStart=%s run -server %s\nRestart=always\nRestartSec=5\nEnvironment=BHUDI_SERVER_URL=%s\n\n[Install]\nWantedBy=default.target\n`,dest,server,server);if err:=os.WriteFile(path,[]byte(userUnit),0644);err!=nil{return err};_=exec.Command("systemctl","--user","daemon-reload").Run();_=exec.Command("systemctl","--user","enable","--now",systemdUnitName).Run();return nil}

func launchdPlistPath()string{home,_:=os.UserHomeDir();return filepath.Join(home,"Library/LaunchAgents/com.bhudi.agent.plist")}
func installLaunchd(dest,server string)error{plist:=launchdPlistPath();_=os.MkdirAll(filepath.Dir(plist),0755);content:=fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>Label</key><string>com.bhudi.agent</string><key>ProgramArguments</key><array><string>%s</string><string>run</string><string>-server</string><string>%s</string></array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/></dict></plist>\n`,dest,server);if err:=os.WriteFile(plist,[]byte(content),0644);err!=nil{return err};_=exec.Command("launchctl","load",plist).Run();return nil}
func copyFile(src,dst string)error{data,err:=os.ReadFile(src);if err!=nil{return err};return os.WriteFile(dst,data,0755)}
