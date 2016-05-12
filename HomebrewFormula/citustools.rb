class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.1.0.tar.gz"
  sha256 "dc773c21989aa4d716b653ed7542d333f63f14a10d470f9a24fe12fac836b262"

  depends_on "uncrustify"

  def install
    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
