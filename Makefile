CXX      := g++
CXXFLAGS := -std=c++17 -O0 -g -Wall -Wextra
LDFLAGS  := -rdynamic

TARGET   := hello
SRCS     := main.cpp
OBJS     := $(SRCS:.cpp=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)
	