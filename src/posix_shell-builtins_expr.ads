with GNAT.OS_Lib; use GNAT.OS_Lib;

package Posix_Shell.Builtins_Expr is

   function Builtin_Expr (Args : String_List) return Integer;
   --  Implement the "printf" builtin.

end Posix_Shell.Builtins_Expr;
