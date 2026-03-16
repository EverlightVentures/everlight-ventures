from pycparser.plyparser import parameterized
#how to print
print (20 * 24 * 60)

#Assign_a_Variable
calculation_to_units = 24*60*60
name_of_unit = "hours"

#concatonate strings long version
print ("20 Days are " + str(50) + " minutes")

#concatonate short version
print (f"20 days are {50} minutes")

#concate with mutliple intergers
print (f"20 days are {20*24*60} minutes")

#concat with variables
print (f"110 days are {calculation_to_units} {name_of_unit}")

# to avoid redundancy we can assign variables and use it in multiple different places

#Functions - define the function with #def
def days_to_units(num_of_days):
    print (f"{num_of_days} days are w{num_of_days * calculation_to_units} {name_of_unit}")
    print ("All good!")
#when you define a function you must use it to print it, how to use it? calling a function using the name of the function with brackerst

#how to use functions so everything else stays the same? give the function an input value or a parameterizer
#define the perameter input within the brackets
#can define as many units
days_to_units(20)
days_to_units(10)
days_to_units(5)


######## Self master quiz - Build my own function ############



variable1 = " Hey, im trying to make my own def functions, can you help?"
variable2 = " Sure! Of course i can, i just took a class. Lets concatonate our sentences"

conversation_1 = "Here is an good example of a concatination " + (variable1 + variable2)
conversation_2 = (f"Here is a better example of a concationation {variable1}{variable2}")


hours_a_day = 1
unit_of_time = "hours"days_a_year = 365
days_a_year = 365
total_study_time = (f"Great, ill spend {hours_a_day}{unit_of_time}, Coding {days_a_year}.")

conversation_3 = (f"Great now i can code {total_study_time * days_a_year} {unit_of_time} a year")
def example_dialogue():
    print(conversation_1)
    print(conversation_2)
    print(conversation_3)
example_dialogue()

""""
def example_dialogue2(converstaion, hours_per_day):
    print(conversation_3, 10)
example_dialogue2()

"""