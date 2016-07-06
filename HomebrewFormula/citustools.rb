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
  url "https://github.com/citusdata/tools/archive/v0.3.1.tar.gz"
  sha256 "bf06e6dafd142ba042f488e3de20405d5473f866a15b6c3228290130bf9ea144"

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
