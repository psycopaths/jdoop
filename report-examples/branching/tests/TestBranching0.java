/*
 * Copyright 2015 Marko Dimjašević
 * 
 * This file is part of JDoop.
 * 
 * JDoop is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * JDoop is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with JDoop.  If not, see <http://www.gnu.org/licenses/>.
*/


import junit.framework.*;

public class TestBranching0 extends TestCase {

  public void test1() throws Throwable {

      branching.Branching b = new branching.Branching();
      int r = b.methodWithBranches(10);
  }

  public void test2() throws Throwable {

      branching.Branching b = new branching.Branching();
      int r = b.methodWithBranches(-42);
  }

  public void test3() throws Throwable {

      branching.Branching b = new branching.Branching();
      int r = b.methodWithBranches(-200);
  }

}
