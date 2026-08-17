//go:build windows

package main

import (
    "fmt"
    "io"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "syscall"
    "time"
    "golang.org/x/sys/windows/registry"
)

const (
    windowsServiceName="BhudiAgent"; windowsTaskName="BhudiAgent"; windowsWatchdogName="BhudiAgentWatchdog"
    uninstallRegPath=`SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\BhudiAgent`; displayName="Bhudi Agent"; publisherName="Bhudi"; runKeyPath=`Software\Microsoft\Windows\CurrentVersion\Run`
)

func installService(server, enrollmentToken string) error {
    server=strings.TrimRight(server,"/"); if strings.TrimSpace(enrollmentToken)==""{return fmt.Errorf("customer enrollment token is required")}
    exe,err:=os.Executable();if err!=nil{return err};exe,_=filepath.Abs(exe)
    destDir:=filepath.Join(os.Getenv("ProgramFiles"),"Bhudi","Agent");if err:=os.MkdirAll(destDir,0755);err!=nil{destDir=filepath.Join(os.Getenv("LOCALAPPDATA"),"Bhudi","Agent");if err:=os.MkdirAll(destDir,0755);err!=nil{return fmt.Errorf("create install dir: %w",err)}}
    dest:=filepath.Join(destDir,"bhudi-agent.exe");if err:=copyFile(exe,dest);err!=nil{return fmt.Errorf("copy agent: %w",err)}
    if err:=os.MkdirAll(dataDir(),0755);err!=nil{return err}; if err:=os.WriteFile(enrollmentTokenPath(),[]byte(strings.TrimSpace(enrollmentToken)),0600);err!=nil{return fmt.Errorf("write enrollment bootstrap: %w",err)}
    if err:=writeConfig(server);err!=nil{fmt.Println("Warning: could not write config:",err)}
    if err:=installWindowsService(dest,server);err!=nil{return err}
    fmt.Println("Windows Service installed:",windowsServiceName,"(Automatic)")
    _=exec.Command("schtasks","/Delete","/TN",windowsWatchdogName,"/F").Run()
    cmdLine:=fmt.Sprintf("\"%s\" run -server %s",dest,server);watch:=exec.Command("schtasks","/Create","/TN",windowsWatchdogName,"/TR",cmdLine,"/SC","MINUTE","/MO","5","/RL","HIGHEST","/F");if out,e:=watch.CombinedOutput();e!=nil{fmt.Printf("Warning: watchdog task failed: %v (%s)\n",e,strings.TrimSpace(string(out)))}
    _=writeRunKey(dest,server);_=writeUninstallRegistry(destDir,dest)
    if err:=startWindowsService();err!=nil{return fmt.Errorf("service installed but could not start: %w",err)}
    fmt.Println("Service started.");fmt.Println("Install complete — native Windows agent; no Python required.");fmt.Println("  Binary:",dest);fmt.Println("  Server:",server);fmt.Println("  Service:",windowsServiceName);time.Sleep(time.Second);return nil
}

func installWindowsService(dest,server string)error{_ = exec.Command("sc","stop",windowsServiceName).Run();_ = exec.Command("sc","delete",windowsServiceName).Run();time.Sleep(500*time.Millisecond);binPath:=fmt.Sprintf("\"%s\" run -server %s",dest,server);create:=exec.Command("sc","create",windowsServiceName,"binPath=",binPath,"start=","auto","DisplayName=",displayName,"obj=","LocalSystem");out,err:=create.CombinedOutput();if err!=nil{return fmt.Errorf("%v: %s",err,strings.TrimSpace(string(out)))};_=exec.Command("sc","description",windowsServiceName,"Bhudi RMM agent — heartbeats, remote access, command execution").Run();_=exec.Command("sc","failure",windowsServiceName,"reset=","86400","actions=","restart/5000/restart/10000/restart/30000").Run();_=exec.Command("sc","failureflag",windowsServiceName,"1").Run();_=exec.Command("sc","config",windowsServiceName,"start=","delayed-auto").Run();return nil}
func startWindowsService()error{out,err:=exec.Command("sc","start",windowsServiceName).CombinedOutput();if err!=nil{msg:=strings.TrimSpace(string(out));if strings.Contains(msg,"1056")||strings.Contains(strings.ToLower(msg),"already"){return nil};return fmt.Errorf("%v: %s",err,msg)};return nil}
func writeRunKey(dest,server string)error{key,_,err:=registry.CreateKey(registry.CURRENT_USER,runKeyPath,registry.SET_VALUE);if err!=nil{return err};defer key.Close();return key.SetStringValue("BhudiAgent",fmt.Sprintf("\"%s\" run -server %s",dest,server))}
func writeUninstallRegistry(installDir,uninstallExe string)error{key,_,err:=registry.CreateKey(registry.LOCAL_MACHINE,uninstallRegPath,registry.ALL_ACCESS);if err!=nil{key,_,err=registry.CreateKey(registry.CURRENT_USER,uninstallRegPath,registry.ALL_ACCESS);if err!=nil{return err}};defer key.Close();_=key.SetStringValue("DisplayName",displayName);_=key.SetStringValue("DisplayVersion",agentVersion);_=key.SetStringValue("Publisher",publisherName);_=key.SetStringValue("InstallLocation",installDir);_=key.SetStringValue("UninstallString",fmt.Sprintf("\"%s\" uninstall",uninstallExe));_=key.SetStringValue("DisplayIcon",uninstallExe);_=key.SetDWordValue("NoModify",1);_=key.SetDWordValue("NoRepair",1);return nil}
func uninstallService()error{_ = exec.Command("sc","stop",windowsServiceName).Run();_ = exec.Command("sc","delete",windowsServiceName).Run();_ = exec.Command("schtasks","/Delete","/TN",windowsTaskName,"/F").Run();_ = exec.Command("schtasks","/Delete","/TN",windowsWatchdogName,"/F").Run();if key,err:=registry.OpenKey(registry.CURRENT_USER,runKeyPath,registry.SET_VALUE);err==nil{_=key.DeleteValue("BhudiAgent");key.Close()};_=registry.DeleteKey(registry.LOCAL_MACHINE,uninstallRegPath);_=registry.DeleteKey(registry.CURRENT_USER,uninstallRegPath);_=os.Remove(identityPath());_=os.Remove(enrollmentTokenPath());fmt.Println("Uninstall complete.");return nil}
func copyFile(src,dst string)error{in,err:=os.Open(src);if err!=nil{return err};defer in.Close();out,err:=os.OpenFile(dst,os.O_CREATE|os.O_WRONLY|os.O_TRUNC,0755);if err!=nil{return err};defer out.Close();_,err=io.Copy(out,in);return err}

var _ = syscall.CREATE_NEW_PROCESS_GROUP
