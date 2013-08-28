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
