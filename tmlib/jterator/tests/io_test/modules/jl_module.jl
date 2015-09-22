importall jtapi

jlfilename = match(r"([^/]+)\.jl$", @__FILE__()).captures[1]

#########
# input #
#########

@printf("jt - %s\n", jlfilename)

handles_stream = readall(STDIN)
handles = readhandles(handles_stream)
input_args = readinput(handles)
input_args = checkinput(input_args)


##############
# processing #
##############

InputVar = input_args["InputVar"]

@printf(">>>>> Image has type \"%s\" and dimensions \"%s\".\n",
        string(typeof(InputVar)), string(size(InputVar)))

println(">>>>> Pixel value at position [2, 3] (1-based): $(InputVar[2, 3])")


data = Dict()
output_args = Dict()
output_args["OutputVar"] = InputVar


##########
# output #
##########

writedata(handles, data)
writeoutput(handles, output_args)
