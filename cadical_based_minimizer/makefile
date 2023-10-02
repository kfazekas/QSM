OBJDIR=build
OBJECTS= qs_minimizer.o coverage_counter.o
OBJS = $(patsubst %.o,$(OBJDIR)/%.o,$(OBJECTS))

SRCDIR=src

FLAGS= -Wall -Werror -Wextra -O3 -DNDEBUG

STANDARD= -std=c++11

CADICAL_INC=./cadical/
CADICAL_LIB_DIR=./cadical/
CADICAL_LIB=-lcadical

all : $(OBJDIR)/main.o
	g++ $(FLAGS) $(OBJDIR)/main.o $(OBJS) -L$(CADICAL_LIB_DIR) $(CADICAL_LIB) -o build/qsm

$(OBJDIR)/main.o : main.cpp $(OBJS) $(SRCDIR)/qs_minimizer.h
	g++ $(FLAGS) $(STANDARD) -I$(CADICAL_INC) -c $< -o $@

$(OBJDIR)/qs_minimizer.o : $(SRCDIR)/qs_minimizer.cpp $(SRCDIR)/qs_minimizer.h 
	g++ $(FLAGS) $(STANDARD) -I$(CADICAL_INC) -c $< -o $@

$(OBJDIR)/coverage_counter.o : $(SRCDIR)/coverage_counter.cpp $(SRCDIR)/coverage_counter.h 
	g++ $(FLAGS) $(STANDARD) -I$(CADICAL_INC) -c $< -o $@

$(shell   mkdir -p $(OBJDIR))

#.PHONY : clean
clean:
	rm -f *.a $(OBJDIR)/*.o *~ *.out  $(OBJDIR)/qsm

tar:
	tar cfv QSM.tar main.cpp makefile LICENSE README $(SRCDIR)/*.cpp $(SRCDIR)/*.h cadical/*.a cadical/*.hpp
