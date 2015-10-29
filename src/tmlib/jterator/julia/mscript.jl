#!/usr/bin/env julia
using MATLAB

# This Julia script turns a Matlab script into a real executable, which 
# can accept standard input within a PIPE. In addition, it preserves the
# current working directory and adds it to the Matlab search path. 
#
# The approach requires an installation of Julia:
#   http://julialang.org/downloads/
# 
# It further depends on the Julia "MATLAB" package:
#   https://github.com/JuliaLang/MATLAB.jl
#
# Author: Markus Herrmann <markus.herrmann@imls.uzh.ch>

 
# get filename of Matlab script
script_path = ARGS[1]
if ~isabspath(script_path)
    script_path = joinpath(pwd(), script_path)
end

# get standard input
input_stream = readall(STDIN)

# start Matlab session
print("Mscript: ")
s1 = MSession()

# send standard input stream into Matlab session
print("Mscript: Forward standard input to Matlab\n")
put_variable(s1, :STDIN, input_stream)

# send current working directory into Matlab session
print("Mscript: Forward current working directory to Matlab\n")
put_variable(s1, :currentDirectory, pwd())

# add current working directory to the Matlab path
print("Mscript: Add current working directory to the Matlab search path\n")
eval_string(s1, "addpath(genpath(currentDirectory))")

# run script within Matlab session
print("Mscript: Run Matlab script...\n\n")
eval_string(s1, @sprintf("run(\'%s\')", script_path))
