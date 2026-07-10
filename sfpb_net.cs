using System;
using System.Runtime.InteropServices;

public class SfpbNet
{
    [UnmanagedCallersOnly(EntryPoint = "net_versiyon_al")]
    public static IntPtr VersiyonAl()
    {
        string v = ".NET 8 Engine Active v0.2.0";
        return Marshal.StringToHGlobalAnsi(v);
    }
}