with GNAT.OS_Lib; use GNAT.OS_Lib;
with Posix_Shell.Annotated_Strings; use Posix_Shell.Annotated_Strings;
with Ada.Containers.Indefinite_Hashed_Maps;
with Ada.Strings.Hash;

package Posix_Shell.Variables is

   type Shell_State is private;
   type Shell_State_Access is access all Shell_State;

   Variable_Name_Error : exception;
   --  An exception raised when an invalid variable name is used.
   --  Invalid in this case is meant from a syntactic point of view;
   --  whether the variable exists or not is irrelevant in this case.

   function Is_Valid_Variable_Name (Name : String) return Boolean;
   --  Return  True if Name is, from a syntactic point of view, a valid
   --  variable name, False otherwise.

   --  function Get_Var_Value (Name : String) return String_Access;
   --  If Name is a defined variable name, then return a pointer
   --  to its current value.  Return null otherwise.
   --
   --  The pointer returned should be deallocated after use.

   function Get_Var_Value (State : Shell_State; Name : String) return String;
   --  Return the value of a variable. The empty string is returned
   --  when the variable is not defined.

   function Get_Var_Value
     (State           : Shell_State;
      Name            : String;
      Context         : Annotation;
      Check_Existence : Boolean    := True)
      return Annotated_String;

   function Is_Var_Set (State : Shell_State; Name : String) return Boolean;

   procedure Import_Environment (State : in out Shell_State);

   function Get_Environment (State : Shell_State) return String_List;

   function Get_Current_Dir
     (State : Shell_State; Strip_Drive : Boolean := False) return String;

   procedure Set_Current_Dir (State : in out Shell_State; Dir : String);

   function Resolve_Path
     (State : Shell_State; Path : String) return String;

   procedure Set_Var_Value
     (State        : in out Shell_State;
      Name         : String;
      Value        : String;
      Export       : Boolean := False;
      Is_Env_Value : Boolean := False);
   --  Set a var value

   procedure Unset_Var (State : in out Shell_State; Name : String);
   --  Unset variable

   procedure Export_Var (State : in out Shell_State; Name : String);
   --  Export a variable

   procedure Export_Var
     (State : in out Shell_State; Name : String; Value : String);
   --  Export variable

   function Enter_Scope (Previous : Shell_State) return Shell_State;
   --  Given the current state create a new scope and return its state

   procedure Leave_Scope
     (Current  : in out Shell_State;
      Previous : in out Shell_State;
      Keep_Pos_Params : Boolean := False);
   --  restore previous env values

   procedure Save_Last_Exit_Status
     (State : in out Shell_State; Exit_Status : Integer);
   --  Save the exit status of the last command we have run.

   function Get_Last_Exit_Status (State : Shell_State) return Integer;
   --  Return the exit code returned by the last command we have run.

   type Pos_Params_State is private;

   procedure Set_Positional_Parameters
     (State : in out Shell_State;
      Args : String_List;
      Free_Previous : Boolean := True);

   function Get_Positional_Parameters
     (State : Shell_State) return Pos_Params_State;

   procedure Restore_Positional_Parameters
     (State : in out Shell_State; Pos_Params : Pos_Params_State);

   procedure Shift_Positional_Parameters
     (State : in out Shell_State; N : Natural; Success : out Boolean);
   --  Shift the positional parameters by N elements. In other words,
   --  ${N+1} becomes $1, ${N+2} becomes $2, etc...  If N is greater
   --  than the number of positional parameters, then the shift is
   --  not performed, and Success is set to False.

   procedure Deallocate (S : in out Shell_State_Access);

   function Get_Loop_Scope_Level (S : Shell_State) return Natural;

   procedure Set_Loop_Scope_Level (S : in out Shell_State; N : Natural);

   type Redirection_States is private;
private

   type Pos_Params_State is record
      Table : String_List_Access := null;
      Shift : Integer := 0;
      Scope : Integer := 0;
   end record;

   type Var_Value is record
      Val         : String_Access;
      Env_Val     : String_Access;
      Is_Exported : Boolean := False;
      Scope_Owner : Natural := 0;
   end record;

   package String_Maps is
     new Ada.Containers.Indefinite_Hashed_Maps
       (String,
        Var_Value,
        Hash => Ada.Strings.Hash,
        Equivalent_Keys => "=");
   use String_Maps;

   type Redirection_State is record
      Fd       : File_Descriptor;
      Filename : String_Access;
      Delete_On_Close : Boolean;
   end record;
   --  State of Stdin, Stdout or Stderr (file descriptor and filename
   --  if relevant).

   type Redirection_States is array (-2 .. 13) of Redirection_State;
   --  State of Stdin, Stdout and Stderr.
   --  ??? brobecker/2007-04-23:
   --  ???    I think that 0 .. 2 are stdin, stdout and stderr,
   --  ???    and 3 .. 4 are pipe-in and pipe-out.

   --  procedure Push_Redirections
   --  (S : Shell_State_Access; R : Redirection_Op_Stack);
   --  Set a new redirection context.


   type Shell_State is record
      Var_Table        : Map;
      Last_Exit_Status : Integer := 0;
      Pos_Params       : Pos_Params_State;
      Scope_Level      : Natural := 1;
      Is_Env_Valid     : Boolean := False;
      Redirections     : Redirection_States;
      Current_Dir      : String_Access := null;
      Loop_Scope_Level : Natural := 0;
   end record;

end Posix_Shell.Variables;
