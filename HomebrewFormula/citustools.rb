class Docker < Requirement
  fatal true
  default_formula "docker"

  satisfy { which "docker" }

  def message
    "Docker is required for this package."
  end
end

class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.4.0.tar.gz"
  sha256 "97ee8978eba59abf517af480880387709a116e76de00fbd5004778342cf462e1"

  depends_on "uncrustify"
  depends_on Docker

  def install
    # FIXME: ensure installdirs runs exactly once
    ENV.deparallelize

    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
